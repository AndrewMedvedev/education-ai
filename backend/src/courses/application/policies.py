# pyright: reportArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.iam.application.dtos.identity import Identity
from src.iam.application.policies import register_policy
from src.iam.domain.vo import PermissionScope

from ..domain.entities import Course, Member
from ..domain.permissions.courses import DELETE, UPDATE
from ..domain.permissions.courses import READ as READ_COURSE
from ..domain.permissions.invitations import INVITE
from ..domain.permissions.practice import READ as READ_PRACTICE
from ..domain.permissions.theory_session import READ as READ_THEORY_SESSION
from ..domain.vo import MemberRole


@dataclass(kw_only=True, slots=True)
class ManageCourseOptions:
    creator_id: UUID
    member_role: MemberRole | None


@dataclass(kw_only=True, slots=True)
class InviteCourseOptions:
    course: Course
    member: Member | None
    role: MemberRole


@register_policy(DELETE, PermissionScope.COURSE)
def can_delete_course(identity: Identity, resource: ManageCourseOptions) -> bool:
    return identity.id == resource.creator_id


@register_policy(UPDATE, PermissionScope.COURSE)
def can_update_course(identity: Identity, resource: ManageCourseOptions) -> bool:
    if identity.id == resource.creator_id:
        return True

    if resource.member_role is None:
        return False

    return resource.member_role == MemberRole.TEACHER


@register_policy(READ_COURSE, PermissionScope.COURSE)
def can_read_course(identity: Identity, resource: ManageCourseOptions) -> bool:
    if identity.id == resource.creator_id:
        return True
    return resource.member_role is not None


def can_take_action(identity: Identity, resource: ManageCourseOptions) -> bool:
    if identity.id == resource.creator_id:
        return True

    if resource.member_role is None:
        return False

    return resource.member_role in {MemberRole.TEACHER, MemberRole.MODERATOR}


@register_policy(INVITE, PermissionScope.COURSE)
def can_invite_in_course(identity: Identity, resource: InviteCourseOptions) -> bool:
    if identity.id == resource.course.creator_id:
        return True

    if resource.member is None:
        return False

    return resource.member.role.can_assign(resource.role)


@register_policy(READ_PRACTICE, PermissionScope.COURSE)
def can_read_practice(identity: Identity, resource: ManageCourseOptions) -> bool:
    return can_take_action(identity, resource)


@register_policy(READ_THEORY_SESSION, PermissionScope.COURSE)
def can_read_theory_session(identity: Identity, resource: ManageCourseOptions) -> bool:
    return can_take_action(identity, resource)
