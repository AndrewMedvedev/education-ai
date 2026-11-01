#!/usr/bin/env python3
"""Prepare internal OAuth accounts, then exec the existing main.py (Python 3.14+).

Usage, with dependencies and infrastructure already available:
    .venv/bin/python -B bootstrap_backend.py
    .venv/bin/python -B bootstrap_backend.py --check
    .venv/bin/python -B bootstrap_backend.py --repair-service-credentials

Container: override CMD with `python -B /app/bootstrap_backend.py`. For persistent
atomic dotenv updates, mount a DIRECTORY, not an individual file, for example:
    docker run --rm --network dio-network \
      --mount type=bind,src=/absolute/backend-runtime,dst=/app/runtime \
      backend-image python -B /app/bootstrap_backend.py --env-file runtime/.env
Put infrastructure/application settings in that directory's .env beforehand.
The alternate .env is loaded into every child environment; the application's
normal project .env is a lower-priority fallback. Relative paths are project-
relative, never cwd-relative. No dependencies or infrastructure are installed.

The normal lifespan is not changed: it repeats migrations and the stock CLI
bootstrap. That CLI also creates user@user.com with its source-defined password.
Configure SUPER_ADMIN_* securely and review that existing application behavior.
All URLs must address this installation (and the same IAM database). Remote
OAuth providers/databases cannot be provisioned or verified through the local DB.

Missing pairs are generated BEFORE normal application imports, because src's
package initializer imports eager HTTP-client settings. These are real proposed
credentials, not validation placeholders: exactly these values are provisioned
if and only if no managed account already exists. Existing incomplete pairs are
never replaced without --repair-service-credentials. No HTTP calls are made by
this script to authenticate against a server which has not started yet.

Ownership is an exact deterministic UUID + name + description + organization
match, not merely a familiar name/client_id. Repair never adopts an unrelated,
deleted, or disabled account. Rotating a managed secret can break other consumers.
There is no atomic transaction spanning PostgreSQL and the filesystem. After a
commit/file failure, rerun --check, then explicitly repair the managed account.
A process crash can leave a private atomic-write temporary file in the config
directory; it is not a backup and must not be used as a recovery credential store.

--check performs no migrations, bootstrap, dotenv writes, or server startup.
It checks migration heads, account state, hash verification, role ownership,
permissions, and local OAuth issuance/identity parsing, not all integrations.
The preparation timeout covers imports and all subprocesses, not server uptime.
Locks coordinate invocations of THIS script, not arbitrary external DB writers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Application imports must be deferred until genuine proposed credentials exist.
# ruff: noqa: PLC0415
import argparse
import asyncio
import contextlib
import fcntl
import io
import json
import logging
import os
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

if TYPE_CHECKING:
    from dotenv.parser import Binding

    from src.iam.domain.entities import ServiceAccount

ROOT = Path(__file__).resolve().parent
MAX_PORT = 65535
MAX_TIMEOUT = 3600
MARKER = "dio.backend.bootstrap/v1"
LOCK_ID = 0x44494F424F4F5431
REQUIRED = {
    "SRV_ORGANIZATION": frozenset({"invitations.invite", "memberships.read"}),
    "SRV_COURSE": frozenset(
        {"invitations.invite", "memberships.read", "organization-invitations.invite"}
    ),
    # CurrentIdentity rejects empty perms, even on auth-only media endpoints.
    "SRV_LLM_ROUTER": frozenset({"permissions.read"}),
}
PREFIXES = (*REQUIRED, "SRV_IAM")
CONTROLLED = frozenset(
    f"{prefix}_{suffix}"
    for prefix in PREFIXES
    for suffix in ("CLIENT_ID", "CLIENT_SECRET", "BASE_URL")
)


class BootstrapError(Exception):
    """Only messages constructed by this script may be displayed to the user."""


@dataclass(repr=False)
class EnvFile:
    path: Path
    original: bytes
    bindings: list[Binding] = field(repr=False)
    values: dict[str, str | None] = field(repr=False)
    existed: bool = False


def read_env(path: Path) -> EnvFile:
    if path.is_symlink():
        raise BootstrapError("Symlink .env is not supported; mount its parent directory instead.")
    existed = path.exists()
    if existed and not stat.S_ISREG(path.stat().st_mode):
        raise BootstrapError("The configuration path must be a regular .env file.")
    original = path.read_bytes() if existed else b""
    return parse_env(path, original, existed=existed)


def parse_env(path: Path, original: bytes, *, existed: bool = True) -> EnvFile:
    from dotenv.parser import parse_stream

    bindings = list(parse_stream(io.StringIO(original.decode("utf-8"))))
    values: dict[str, str | None] = {}
    for binding in bindings:
        if binding.error:
            raise BootstrapError(f"Invalid dotenv syntax at line {binding.original.line}.")
        key = binding.key
        if key is None:
            continue
        if key.upper() in CONTROLLED and (key != key.upper() or key in values):
            raise BootstrapError(
                "Service settings must use unique uppercase dotenv keys "
                "(no duplicate assignments)."
            )
        values[key] = binding.value
    return EnvFile(path, original, bindings, values, existed)


def expand_values(values: Mapping[str, str | None], base: Mapping[str, str]) -> dict[str, str]:
    from dotenv.variables import parse_variables

    result: dict[str, str] = {}
    for key, value in values.items():
        if value is not None:
            namespace = result | dict(base)  # load_dotenv(override=False) semantics
            result[key] = "".join(atom.resolve(namespace) for atom in parse_variables(value))
    return result


def resolve_environment(target: EnvFile, external: Mapping[str, str]) -> dict[str, str]:
    environment = dict(external)
    sources = [target]
    if target.path != ROOT / ".env":
        sources.append(read_env(ROOT / ".env"))
    for source in sources:
        for key, value in expand_values(source.values, environment).items():
            environment.setdefault(key, value)
    # Pydantic settings are case-insensitive. Reject ambiguous spellings rather
    # than silently allowing load_dotenv to invert environment precedence.
    for key in environment:
        if key.upper() in CONTROLLED and key != key.upper():
            raise BootstrapError("Service environment keys must be uppercase.")
    return environment


def load_environment(path: Path) -> tuple[EnvFile, dict[str, str]]:
    target = read_env(path)
    return target, resolve_environment(target, os.environ)


def literal_dotenv(value: str) -> str:
    # python-dotenv interpolates even single-quoted strings. An empty-name
    # default emits a literal dollar without recursive interpolation; a process
    # environment cannot contain an empty-name variable. Verify every roundtrip.
    return value.replace("${", "${:-$}{")


def quote_dotenv(value: str) -> str:
    return "'" + literal_dotenv(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def assignment_suffix(text: str) -> str:
    """Retain the comment/newline after a parsed dotenv value, including multiline quotes."""
    if text.startswith(("'", '"')):
        quote = text[0]
        index = 1
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == quote:
                return text[index + 1 :]
            index += 1
        raise BootstrapError("Cannot safely rewrite a quoted dotenv assignment.")
    line = text.rstrip("\r\n")
    comment = re.search(r"\s+#", line)
    return text[comment.start() :] if comment else text[len(line) :]


def render_env(source: EnvFile, updates: Mapping[str, str]) -> bytes:
    if not updates.keys() <= CONTROLLED:
        raise BootstrapError("Attempt to update a non-service dotenv setting was refused.")
    remaining = dict(updates)
    parts: list[str] = []
    for binding in source.bindings:
        original = binding.original.string
        if binding.key not in remaining:
            parts.append(original)
            continue
        key = binding.key
        match = re.match(r"(\s*(?:export[ \t]+)?" + re.escape(key) + r")[ \t]*", original)
        if match is None:
            raise BootstrapError("Cannot safely identify a dotenv assignment.")
        rest = original[match.end() :]
        suffix = assignment_suffix(rest[1:].lstrip(" \t")) if rest.startswith("=") else rest
        parts.append(f"{match[1]}={quote_dotenv(remaining.pop(key))}{suffix}")
    text = "".join(parts)
    newline = "\r\n" if b"\r\n" in source.original else "\n"
    if remaining and text and not text.endswith(("\n", "\r")):
        text += newline
    text += "".join(f"{key}={quote_dotenv(value)}{newline}" for key, value in remaining.items())
    return text.encode("utf-8")


@contextlib.contextmanager
def staged_env(source: EnvFile, updates: Mapping[str, str]) -> Iterator[Path | None]:
    """Fsync a private temporary file BEFORE DB commit; publish it only afterwards."""
    if not updates:
        yield None
        return
    if source.existed and not source.path.stat().st_mode & 0o222:
        raise BootstrapError("The .env file is read-only; credential publication was refused.")
    if source.path.is_mount():
        raise BootstrapError(
            "Cannot atomically replace a file bind-mounted as .env; mount a writable DIRECTORY."
        )
    descriptor, name = tempfile.mkstemp(prefix=".env.bootstrap-", dir=source.path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(render_env(source, updates))
            stream.flush()
            os.fsync(stream.fileno())
        yield temporary
    finally:
        temporary.unlink(missing_ok=True)


def publish_env(source: EnvFile, temporary: Path | None) -> None:
    if temporary is None:
        return
    if source.path.is_symlink() or source.path.exists() != source.existed:
        raise BootstrapError("The .env file changed concurrently; DB may already be committed.")
    if source.existed and source.path.read_bytes() != source.original:
        raise BootstrapError(
            "The .env contents changed concurrently; DB may already be committed."
        )
    os.replace(temporary, source.path)
    directory = os.open(source.path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@contextlib.contextmanager
def directory_lock(path: Path, timeout: float) -> Iterator[None]:
    # Lock the directory inode: atomic replacement of .env cannot invalidate it,
    # and no additional permanent lock file (or secret file) is needed.
    descriptor = os.open(path.parent, os.O_RDONLY)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise BootstrapError(
                        "Timed out waiting for another bootstrap on this directory."
                    ) from None
                time.sleep(0.1)
        yield
    finally:
        os.close(descriptor)


def setting(environment: Mapping[str, str], key: str, default: str) -> str:
    matches = [value for name, value in environment.items() if name.upper() == key]
    if len(matches) > 1:
        raise BootstrapError("Ambiguous case variants in application/database configuration.")
    return matches[0] if matches else default


def managed_id(kind: str, prefix: str, organization_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"{MARKER}/{organization_id}/{kind}/{prefix}")


def managed_name(prefix: str) -> str:
    return f"{MARKER}:{prefix}"


def account_is_managed(account: ServiceAccount, prefix: str, organization_id: UUID) -> bool:
    return (
        account.id == managed_id("account", prefix, organization_id)
        and account.name == managed_name(prefix)
        and account.description == managed_name(prefix)
        and account.organization_id == organization_id
    )


def credential_action(*, status: str, managed: bool, repair: bool, prefix: str) -> str:
    """Fail-closed policy; separate from I/O to make edge cases independently testable."""
    if status == "valid":
        return "keep"
    if status in {"disabled", "deleted", "foreign-organization", "ambiguous"}:
        raise BootstrapError(f"{prefix}: {status}; automatic recovery is forbidden.")
    if status == "absent" and not managed:
        return "create"
    if (
        repair
        and managed
        and status in {"absent", "incomplete", "unknown-client-id", "bad-secret"}
    ):
        return "rotate"
    recovery = (
        " Use --repair-service-credentials for this bootstrap-owned account."
        if managed
        else " No unambiguous bootstrap-owned account is available for recovery."
    )
    raise BootstrapError(f"{prefix}: {status}.{recovery}")


def migration_command(environment: Mapping[str, str], timeout: float) -> None:
    # Do not expose potentially sensitive third-party tracebacks, SQL, or settings
    # dumps. The stage and exit code are reported by our own diagnostic instead.
    result = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise BootstrapError(
            f"Alembic upgrade head failed (exit {result.returncode}); server was not started. "
            "Check migration/import/configuration errors in an isolated environment."
        )


def configuration_updates(
    source: EnvFile,
    desired: Mapping[str, str],
    effective: Mapping[str, str],
    external: Mapping[str, str],
) -> dict[str, str]:
    updates = {
        key: value
        for key, value in desired.items()
        if source.values.get(key) != literal_dotenv(value)
    }
    candidate = parse_env(source.path, render_env(source, updates))
    independent = resolve_environment(
        candidate, {key: value for key, value in external.items() if key not in CONTROLLED}
    )
    if any(independent.get(key) != value for key, value in desired.items()):
        raise BootstrapError(
            "Service credentials do not round-trip through dotenv; commit refused."
        )
    launched = resolve_environment(candidate, dict(external) | dict(desired))
    nonservice = (effective.keys() | launched.keys()) - CONTROLLED
    if any(effective.get(key) != launched.get(key) for key in nonservice):
        raise BootstrapError(
            "Changing service settings changes another effective dotenv setting through "
            "interpolation; decouple non-service settings from service credentials "
            "before retrying."
        )
    return updates


async def prepare(  # noqa: C901, PLR0912, PLR0915 - sequential bootstrap under one DB lock
    args, source: EnvFile, environment: dict[str, str], external: dict[str, str], report: dict
) -> list[str]:
    import asyncpg

    report["stage"] = "configuration"
    specs = dict(REQUIRED)
    if environment.get("SRV_IAM_CLIENT_ID") or environment.get("SRV_IAM_CLIENT_SECRET"):
        specs["SRV_IAM"] = frozenset()
    original_pairs: dict[str, tuple[str, str]] = {}

    desired: dict[str, str] = {}
    port = int(setting(environment, "APP_PORT", "8000"))
    if not 0 < port <= MAX_PORT:
        raise BootstrapError("APP_PORT must be between 1 and 65535.")
    missing: list[str] = []
    for prefix in specs:
        id_key, secret_key = f"{prefix}_CLIENT_ID", f"{prefix}_CLIENT_SECRET"
        client_id, secret = environment.get(id_key, ""), environment.get(secret_key, "")
        original_pairs[prefix] = (client_id, secret)
        if not client_id or not secret:
            missing.extend(key for key in (id_key, secret_key) if not environment.get(key))
            if args.check:
                continue
            if prefix == "SRV_IAM" or (
                (client_id or secret) and not args.repair_service_credentials
            ):
                raise BootstrapError(
                    f"{prefix}: incomplete credentials; explicit repair is required."
                )
            # Real proposed values, later either persisted unchanged or discarded on
            # failure. Never request a token or start a server with unverified values.

            environment[id_key] = client_id or secrets.token_urlsafe(16)
            environment[secret_key] = secret or secrets.token_urlsafe(32)
        url_key = f"{prefix}_BASE_URL"
        url = environment.get(url_key, "")
        if not url:
            if args.check:
                missing.append(url_key)
                continue
            url = f"http://127.0.0.1:{port}"
            environment[url_key] = url
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            raise BootstrapError(
                f"{url_key}: expected an HTTP(S) service URL without credentials."
            )
        desired[url_key] = url
    if missing and args.check:
        raise BootstrapError("Missing effective settings: " + ", ".join(missing))
    os.environ.update(environment)

    # Normal imports only. In particular, do not bypass src/__init__.py. Imports
    # can fail during an in-progress refactor; in that case no DB is even opened.
    report["stage"] = "application imports (including the current AI refactor)"
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import or_, select, text

    from src.cli import commands
    from src.core.database import import_all_models, session_factory
    from src.core.database.connection import engine
    from src.core.settings import INSTALLED_MODULES, super_admin_config
    from src.iam.application.services.oauth import _create_token_for_service_account
    from src.iam.dependencies.identity import _build_identity_from_payload
    from src.iam.domain.entities import Role, ServiceAccount
    from src.iam.domain.permissions.registry import get_permissions
    from src.iam.domain.services import validate_roles_assignment
    from src.iam.domain.vo import PermissionGrant, PermissionScope, SecretHash
    from src.iam.infra.database.models import RoleOrm, ServiceAccountOrm
    from src.iam.infra.database.repos.role import SqlRoleRepository
    from src.iam.infra.database.repos.service_account import SqlServiceAccountRepository
    from src.iam.security import (
        decode_token,
        generate_client_secret,
        hash_password_async,
        verify_password_async,
    )
    from src.organization.infra.database.models import OrganizationOrm
    from src.organization.infra.database.repos.organization import SqlOrganizationRepository

    import_all_models(INSTALLED_MODULES)
    # Use the exact parsed DB settings, including URI behavior, used by repositories.
    from src.core.database.config import postgres_config

    report["stage"] = "PostgreSQL bootstrap lock"
    connection = await asyncpg.connect(
        dsn=postgres_config.uri.replace("postgresql+asyncpg://", "postgresql://", 1),
        timeout=min(args.timeout, 15),
        command_timeout=min(args.timeout, 30),
        server_settings={"application_name": "dio-service-bootstrap"},
    )
    deadline = time.monotonic() + args.lock_timeout
    try:
        while not await connection.fetchval("SELECT pg_try_advisory_lock($1)", LOCK_ID):
            if time.monotonic() >= deadline:
                raise BootstrapError("Timed out waiting for another bootstrap in this database.")
            await asyncio.sleep(0.1)
        if not args.check:
            report["stage"] = "Alembic migrations"
            await asyncio.to_thread(migration_command, environment, args.timeout)

        report["stage"] = "migration heads"
        async with engine.connect() as database:
            current = await database.run_sync(
                lambda sync: set(MigrationContext.configure(sync).get_current_heads())
            )
        expected = set(ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads())
        if current != expected:
            raise BootstrapError("Database migration heads do not match this checkout.")

        report["stage"] = "system organization / stock bootstrap"
        async with session_factory() as session:
            organization = await SqlOrganizationRepository(session).get_by_email(
                super_admin_config.email
            )
            if organization and (not organization.is_active or organization.is_deleted):
                raise BootstrapError("The configured system organization is disabled or deleted.")
        if not args.check:
            await commands.create_permissions()
            await commands.create_first_admin()
            await commands.create_default_organization()
            report["notes"].append(
                "Stock bootstrap completed (including its built-in admin/demo-user behavior)."
            )
        else:
            # The stock CLI exposes no public read-only registry loader.
            commands._load_system_permission_modules()  # noqa: SLF001

        report["stage"] = "service account verification / preparation"
        # One transaction for ALL managed roles/accounts, independent from the
        # separately committed stock bootstrap. Rollback on every failed validation.
        async with session_factory() as session:
            if args.check:
                await session.execute(text("SET TRANSACTION READ ONLY"))
            await session.execute(text("SET LOCAL statement_timeout = '30s'"))
            await session.execute(text("SET LOCAL lock_timeout = '10s'"))
            org_models = (
                await session.scalars(
                    select(OrganizationOrm).where(
                        OrganizationOrm.email == super_admin_config.email
                    )
                )
            ).all()
            if len(org_models) != 1:
                raise BootstrapError("The configured system organization is missing or ambiguous.")
            org = org_models[0]
            if not org.is_active or org.deleted_at is not None:
                raise BootstrapError("The configured system organization is disabled or deleted.")
            account_repo = SqlServiceAccountRepository(session)
            role_repo = SqlRoleRepository(session)
            registry = {permission.code: permission for permission in get_permissions()}

            async def managed_role(prefix: str, required: frozenset[str]) -> Role:
                code = f"bootstrap_{prefix.lower()}_v1"
                uid = managed_id("role", prefix, org.id)
                models = (
                    await session.scalars(
                        select(RoleOrm)
                        .where(or_(RoleOrm.id == uid, RoleOrm.code == code))
                        .with_for_update()
                    )
                ).all()
                if models:
                    if len(models) != 1:
                        raise BootstrapError(
                            f"{prefix}: ambiguous managed roles; recovery refused."
                        )
                    role = role_repo.model_mapper.from_model(models[0])
                    if (
                        role.id != uid
                        or role.code != code
                        or role.description != managed_name(prefix)
                        or role.organization_id != org.id
                        or role.is_default
                        or role.is_deleted
                    ):
                        raise BootstrapError(
                            f"{prefix}: role ownership conflict; recovery refused."
                        )
                    existing = {grant.permission for grant in role.permissions}
                    if not required <= existing:
                        if not args.repair_service_credentials:
                            raise BootstrapError(
                                f"{prefix}: insufficient managed-role permissions."
                            )
                        for permission in required - existing:
                            role.grant_permission(permission, grant_scope(permission))
                        await role_repo.upsert(role)
                    return role
                role = Role(
                    id=uid,
                    name=managed_name(prefix),
                    code=code,
                    description=managed_name(prefix),
                    organization_id=org.id,
                    permissions={
                        PermissionGrant(permission=p, scope=grant_scope(p)) for p in required
                    },
                )
                await role_repo.create(role)
                return role

            def grant_scope(permission: str) -> PermissionScope:
                scope = (
                    PermissionScope.GLOBAL
                    if permission == "permissions.read"
                    else PermissionScope.ORGANIZATION
                )
                if permission not in registry or scope not in registry[permission].scopes:
                    raise BootstrapError(
                        "Required permission/scope is absent from the application registry."
                    )
                return scope

            async def verify_roles(account: ServiceAccount, required: frozenset[str]) -> bool:
                roles = await role_repo.get_by_ids(list(account.roles))
                if len(roles) != len(account.roles) or any(role.is_deleted for role in roles):
                    raise BootstrapError("A service account references missing/deleted roles.")
                validate_roles_assignment(roles, org.id)
                return (
                    bool(roles)
                    and bool({g.permission for r in roles for g in r.permissions})
                    and required
                    <= {grant.permission for role in roles for grant in role.permissions}
                )

            for prefix, required in specs.items():
                client_id, secret = original_pairs[prefix]
                uid = managed_id("account", prefix, org.id)
                owned_query = select(ServiceAccountOrm).where(
                    or_(
                        ServiceAccountOrm.id == uid,
                        ServiceAccountOrm.name == managed_name(prefix),
                        ServiceAccountOrm.description == managed_name(prefix),
                    )
                )
                if not args.check:
                    owned_query = owned_query.with_for_update()
                owned_models = (await session.scalars(owned_query)).all()
                if len(owned_models) > 1:
                    raise BootstrapError(f"{prefix}: ambiguous bootstrap account duplicates.")
                owned = (
                    account_repo.model_mapper.from_model(owned_models[0]) if owned_models else None
                )
                if owned and not account_is_managed(owned, prefix, org.id):
                    raise BootstrapError(
                        f"{prefix}: managed-account ownership conflict; recovery refused."
                    )
                selected_query = select(ServiceAccountOrm).where(
                    ServiceAccountOrm.client_id == client_id
                )
                if not args.check:
                    selected_query = selected_query.with_for_update()
                selected_models = (
                    (await session.scalars(selected_query)).all() if client_id else []
                )
                if len(selected_models) > 1:
                    raise BootstrapError(f"{prefix}: ambiguous client_id duplicates.")
                selected = (
                    account_repo.model_mapper.from_model(selected_models[0])
                    if selected_models
                    else None
                )
                for candidate in (owned, selected):
                    if candidate and (not candidate.is_active or candidate.is_deleted):
                        status = "deleted" if candidate.is_deleted else "disabled"
                        credential_action(
                            status=status, managed=bool(owned), repair=False, prefix=prefix
                        )
                if selected and selected.organization_id != org.id:
                    credential_action(
                        status="foreign-organization", managed=False, repair=False, prefix=prefix
                    )

                if not client_id and not secret:
                    status = "absent"
                elif not client_id or not secret:
                    status = "incomplete"
                elif selected is None:
                    status = "unknown-client-id"
                elif not await verify_password_async(
                    secret, selected.client_secret_hash.get_hashed_value()
                ):
                    status = "bad-secret"
                else:
                    status = "valid"
                repair_owned = owned is not None and (selected is None or selected.id == owned.id)
                if args.check and status != "valid":
                    raise BootstrapError(f"{prefix}: {status}; --check does not change data.")
                action = credential_action(
                    status=status,
                    managed=repair_owned,
                    repair=args.repair_service_credentials and prefix != "SRV_IAM",
                    prefix=prefix,
                )
                if prefix == "SRV_IAM" and action != "keep":
                    raise BootstrapError(
                        "SRV_IAM is not provisioned: no active consumer was found."
                    )
                if action == "create":
                    role = await managed_role(prefix, required)
                    validate_roles_assignment([role], org.id)
                    client_id = environment[f"{prefix}_CLIENT_ID"]
                    secret = environment[f"{prefix}_CLIENT_SECRET"]
                    account = ServiceAccount(
                        id=uid,
                        name=managed_name(prefix),
                        description=managed_name(prefix),
                        organization_id=org.id,
                        roles={role.id},
                        client_id=client_id,
                        client_secret_hash=SecretHash(await hash_password_async(secret)),
                    )
                    await account_repo.create(account)
                elif action == "rotate":
                    if owned is None:
                        raise BootstrapError(f"{prefix}: managed recovery target disappeared.")
                    account = owned
                    client_id, secret = account.client_id, generate_client_secret()
                    await account_repo.update(
                        account.id, client_secret_hash=await hash_password_async(secret)
                    )
                    report["notes"].append(
                        f"{prefix}: managed secret rotated; other consumers may need updating."
                    )
                else:
                    if selected is None:
                        raise BootstrapError(f"{prefix}: verified account disappeared.")
                    account = selected
                await session.flush()
                if not await verify_roles(account, required):
                    if (
                        args.check
                        or not args.repair_service_credentials
                        or not account_is_managed(account, prefix, org.id)
                    ):
                        raise BootstrapError(
                            f"{prefix}: insufficient permissions; "
                            "unrelated accounts are never elevated."
                        )
                    role = await managed_role(prefix, required)
                    account.roles.add(role.id)
                    await account_repo.update(
                        account.id, roles=[str(role_id) for role_id in account.roles]
                    )
                    await session.flush()
                    report["notes"].append(f"{prefix}: managed service role assigned.")
                # Re-fetch and authenticate the persisted state, then use the
                # identical token builder used by OAuthService.issue_token().
                persisted = await account_repo.get_by_client_id(client_id)
                if (
                    persisted is None
                    or not persisted.is_active
                    or not await verify_password_async(
                        secret, persisted.client_secret_hash.get_hashed_value()
                    )
                ):
                    raise BootstrapError(f"{prefix}: persisted credentials failed verification.")
                token = _create_token_for_service_account(
                    persisted, await role_repo.get_by_ids(list(persisted.roles))
                )
                identity = _build_identity_from_payload(decode_token(token.access_token))
                if (
                    identity.id != account.id
                    or identity.organization_id != org.id
                    or not required <= identity.permissions
                ):
                    raise BootstrapError(f"{prefix}: OAuth identity/permissions mismatch.")
                desired[f"{prefix}_CLIENT_ID"] = client_id
                desired[f"{prefix}_CLIENT_SECRET"] = secret
                report["notes"].append(
                    f"{prefix}: {action}; active account, secret, "
                    "organization and permissions verified."
                )

            if args.check:
                await session.rollback()
                return []
            updates = configuration_updates(source, desired, environment, external)
            report["stage"] = (
                "private dotenv staging / database commit / atomic dotenv publication"
            )
            with staged_env(source, updates) as temporary:
                # If commit outcome is uncertain, do NOT publish an unverified file.
                report["commit_attempted"] = True
                await session.commit()
                report["committed"] = True
                publish_env(source, temporary)
            # Only key names cross the result pipe; secrets remain in DB/.env/env.
            return list(desired)
    finally:
        await connection.close(timeout=5)
        await engine.dispose()


def safe_error(exc: Exception, report: dict) -> str:
    if isinstance(exc, BootstrapError):
        message = str(exc)
    else:
        # Pydantic/SQL/driver exception messages may contain credentials. Never
        # stringify, serialize, or print these exceptions or their tracebacks.
        message = (
            f"Preparation failed during {report['stage']} ({type(exc).__name__}); "
            "details suppressed to protect secrets."
        )
    if report.get("commit_attempted"):
        message += (
            " Database commit was attempted: DB/file consistency is NOT guaranteed. "
            "Run --check, then explicitly --repair-service-credentials if needed. "
            "Do not delete accounts or try to recover a secret from its hash."
        )
    return message


def worker(args) -> int:
    report = {"ok": False, "stage": "dotenv loading", "notes": []}
    logging.disable(logging.CRITICAL)
    # Import-time output and third-party diagnostics must not leak settings. Our
    # sole stdout protocol contains only fixed diagnostics and verified key names.
    with (
        open(os.devnull, "w") as sink,
        contextlib.redirect_stdout(sink),
        contextlib.redirect_stderr(sink),
    ):
        try:
            external = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            source, environment = load_environment(args.env_file)
            os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            verified = asyncio.run(prepare(args, source, environment, external, report))
            report.update(ok=True, verified=verified)
        except Exception as exc:  # noqa: BLE001 - redact, report failure, exit nonzero
            report["error"] = safe_error(exc, report)
    print(json.dumps(report, ensure_ascii=True), flush=True)
    return 0 if report["ok"] else 1


def supervise(args) -> int:  # noqa: C901 - bounded child lifecycle and exec handoff
    started = time.monotonic()
    with directory_lock(args.env_file, args.lock_timeout):
        _, initial_environment = load_environment(args.env_file)
        command = [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--_prepare",
            "--env-file",
            str(args.env_file),
            "--timeout",
            str(args.timeout),
            "--lock-timeout",
            str(args.lock_timeout),
        ]
        if args.check:
            command.append("--check")
        if args.repair_service_credentials:
            command.append("--repair-service-credentials")
        # New session lets timeout and termination kill the whole preparation
        # tree, including Alembic, before any main.py can be launched.
        process = subprocess.Popen(  # noqa: S603 - trusted interpreter/script; no shell
            command,
            cwd=ROOT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
        )
        previous_handlers = {}

        def forward_signal(number, _frame):
            os.killpg(process.pid, number)

        try:
            for number in (signal.SIGTERM, signal.SIGINT):
                previous_handlers[number] = signal.signal(number, forward_signal)
            try:
                output, _ = process.communicate(
                    timeout=max(0.01, args.timeout - (time.monotonic() - started))
                )
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise BootstrapError(
                    "Preparation timed out and its process group was stopped. A DB commit/file "
                    "publication may have been interrupted; "
                    "run --check and explicit repair if needed."
                ) from None
        finally:
            for number, handler in previous_handlers.items():
                signal.signal(number, handler)
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        if process.returncode is None or process.returncode < 0:
            raise BootstrapError(
                "Preparation was interrupted; verify DB/file consistency with --check."
            )
        try:
            report = json.loads(output)
        except ValueError, TypeError:
            raise BootstrapError(
                "Preparation returned no valid status; server was not started."
            ) from None
        if process.returncode or not report.get("ok"):
            raise BootstrapError(
                report.get("error", "Preparation failed; server was not started.")
            )
        for note in report.get("notes", []):
            print(note, file=sys.stderr)
        if args.check:
            print("Check passed. No data changed; no integrations or HTTP server were started.")
            return 0
        source = read_env(args.env_file)
        environment = initial_environment
        published = resolve_environment(
            source, {key: value for key, value in environment.items() if key not in CONTROLLED}
        )
        verified = report.get("verified", [])
        if not set(verified) <= CONTROLLED:
            raise BootstrapError(
                "Invalid configuration verification report; server was not started."
            )
        for key in verified:
            if key not in published:
                raise BootstrapError(
                    "Published configuration is incomplete; server was not started."
                )
            # Override EVERY verified service setting, not merely keys rewritten
            # in the file: a corrected client_id may already have been present there.
            environment[key] = published[key]
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        print("Preparation complete. Starting existing main.py.", file=sys.stderr, flush=True)
        os.chdir(ROOT)
        # Direct exec is intentional: preserve signals and exit status without a shell.
        os.execve(  # noqa: S606
            sys.executable, [sys.executable, "-B", str(ROOT / "main.py")], environment
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify only; no writes, migrations or server."
    )
    parser.add_argument(
        "--repair-service-credentials",
        action="store_true",
        help=(
            "Explicitly repair only bootstrap-owned accounts; rotation can break other consumers."
        ),
    )
    parser.add_argument(
        "--env-file", default=".env", help="Project-relative or absolute writable .env path."
    )
    parser.add_argument(
        "--timeout", type=float, default=300, help="Total preparation deadline in seconds."
    )
    parser.add_argument(
        "--lock-timeout", type=float, default=30, help="Bounded lock wait in seconds."
    )
    parser.add_argument(
        "--_prepare", dest="prepare_worker", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    if args.check and args.repair_service_credentials:
        parser.error("--check and --repair-service-credentials cannot be combined")
    if not 0 < args.lock_timeout <= args.timeout <= MAX_TIMEOUT:
        parser.error("require 0 < lock-timeout <= timeout <= 3600 seconds")
    path = Path(args.env_file)
    args.env_file = (ROOT / path if not path.is_absolute() else path).absolute()
    if args.env_file.name != ".env" or not args.env_file.parent.is_dir():
        parser.error("--env-file must name .env inside an existing directory")
    try:
        if args.prepare_worker:
            return worker(args)
        if args.repair_service_credentials:
            print(
                "WARNING: managed credential rotation can break other consumers and workers.",
                file=sys.stderr,
            )
        return supervise(args)
    except BootstrapError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - never leak arbitrary exception payloads
        print(
            f"ERROR: launcher failed ({type(exc).__name__}); "
            "details suppressed to protect secrets.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
