# API модуля `iam`

Глобальный префикс: `/api/v1` (`backend/src/__init__.py`).

## Общие форматы

### `DomainError`

```json
{"error":{"code":"UNAUTHORIZED","message":"Требуется авторизация","details":{}}}
```

### `ValueError`

```json
{"error":{"grant":"VALIDATION_ERROR","message":"...","status":400,"details":{}}}
```

### FastAPI/Pydantic validation

```json
{"detail":[{"loc":["body","email"],"msg":"...","type":"..."}]}
```

## Обзор endpoints

| Метод | Путь | Назначение | Авторизация | Файл |
|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Login email/password | Нет | `api/v1/auth.py` |
| POST | `/api/v1/auth/token` | Exchange authentication token to JWT | Нет | `api/v1/auth.py` |
| POST | `/api/v1/auth/token/refresh` | Refresh tokens | Нет | `api/v1/auth.py` |
| POST | `/api/v1/auth/logout` | Blacklist tokens | Нет | `api/v1/auth.py` |
| GET | `/api/v1/auth/identity` | Current identity | Bearer | `api/v1/auth.py` |
| POST | `/api/v1/oauth/token` | Client credentials token | Нет | `api/v1/oauth.py` |
| GET | `/api/v1/users/me` | Текущий user | Bearer | `api/v1/users.py` |
| PATCH | `/api/v1/users/me` | Обновить текущего user | Bearer | `api/v1/users.py` |
| POST | `/api/v1/users/search` | Поиск users | Bearer | `api/v1/users.py` |
| GET | `/api/v1/users/{user_id}` | User by id | Bearer | `api/v1/users.py` |
| GET | `/api/v1/users/by-email/{email}` | User by email | Bearer | `api/v1/users.py` |
| POST | `/api/v1/roles` | Создать role | `roles.create` | `api/v1/roles.py` |
| PATCH | `/api/v1/roles/{role_id}` | Обновить role | `roles.update` | `api/v1/roles.py` |
| GET | `/api/v1/roles` | Список roles | `roles.read` | `api/v1/roles.py` |
| GET | `/api/v1/roles/{role_id}` | Role by id | `roles.read` | `api/v1/roles.py` |
| DELETE | `/api/v1/roles/{role_id}` | Удалить role | `roles.delete` | `api/v1/roles.py` |
| POST | `/api/v1/roles/{role_id}/permissions` | Grant permission | Не задана; handler stub | `api/v1/roles.py` |
| DELETE | `/api/v1/roles/{role_id}/permissions/{permission}` | Revoke permission | Не задана; handler stub | `api/v1/roles.py` |
| GET | `/api/v1/permissions` | Registry permissions | `permissions.read` | `api/v1/permissions.py` |
| POST | `/api/v1/memberships` | Create membership | `memberships.create` | `api/v1/memberships.py` |
| GET | `/api/v1/memberships/{organization_id}/{user_id}` | Get membership | `memberships.read` | `api/v1/memberships.py` |
| POST | `/api/v1/invitations` | Create invitation | `invitations.invite` | `api/v1/invitations.py` |
| POST | `/api/v1/invitations/accept/{token}` | Accept invitation | Нет | `api/v1/invitations.py` |
| DELETE | `/api/v1/invitations/revoke/{invitation_id}` | Revoke invitation | `invitations.delete` | `api/v1/invitations.py` |
| POST | `/api/v1/service-accounts` | Create service account | Не задана | `api/v1/service_accounts.py` |
| POST | `/api/v1/service-accounts/search` | Search service accounts | Не задана | `api/v1/service_accounts.py` |
| GET | `/api/v1/service-accounts/{service_account_id}` | Get service account | Не задана | `api/v1/service_accounts.py` |
| PATCH | `/api/v1/service-accounts/{service_account_id}` | Update service account | Не задана | `api/v1/service_accounts.py` |
| DELETE | `/api/v1/service-accounts/{service_account_id}` | Delete service account | Не задана | `api/v1/service_accounts.py` |

## Endpoints

### POST `/api/v1/auth/login`

**Назначение:** проверяет email/password и возвращает short-lived authentication token + memberships.

**Авторизация:** не требуется.

**Тело:** `UserCredentials`.

| Поле | Тип | Обяз. | Ограничения | Описание |
|---|---|---:|---|---|
| `email` | `EmailStr` | да | валидный email | Email пользователя |
| `password` | `str` | да | Pydantic string | Пароль |

Пример:

```json
{"email":"user@example.com","password":"secret"}
```

**Успешный ответ:** `200 OK`, `LoginResponse`.

```json
{"authentication_token":"...","memberships":[{"id":"00000000-0000-0000-0000-000000000000","joined_at":"2026-01-01T00:00:00Z","organization":{"id":"00000000-0000-0000-0000-000000000000","name":"Org"}}]}
```

**Ошибки:** 401 invalid credentials, 422 invalid body, 500. **Побочные эффекты:** нет. **Идемпотентность:** да.

### POST `/api/v1/auth/token`

**Тело:** `TokenRequest` (`authentication_token`, `membership_id`).

**Ответ:** `200 OK`, `TokensResponse`:

```json
{"access_token":"...","refresh_token":"...","token_type":"Bearer","expires_at":3600}
```

**Ошибки:** 401 invalid token, 404 membership/user not found, 422, 500. **Побочные эффекты:** выдача JWT. **Идемпотентность:** нет, токены новые.

### POST `/api/v1/auth/token/refresh`

**Тело:** строка `refresh_token` (по сигнатуре `refresh_token: str`).

**Ответ:** `200 OK`, `TokensResponse`. **Ошибки:** 401 invalid/revoked token, 422, 500. **Побочные эффекты:** новые JWT; старый токен может быть проверен against blacklist. **Идемпотентность:** нет.

### POST `/api/v1/auth/logout`

**Тело:** `LogoutRequest` (`access_token`, `refresh_token`).

**Ответ:** объявлен `200 OK`; аннотация endpoint — `TokensResponse`, но сервис по анализу возвращает `None`.

**Ошибки:** 401 invalid token, 422, 500. **Побочные эффекты:** blacklist tokens in Redis. **Идемпотентность:** повторный logout зависит от blacklist implementation.

### GET `/api/v1/auth/identity`

**Авторизация:** Bearer JWT (`CurrentIdentity`).

**Ответ:** `200 OK`, `IdentityResponse`: `id`, `type`, `email`, `organization_id`, `membership_id`, `roles`, `permissions`.

**Ошибки:** 401, 400 invalid claims/VO, 500. **Побочные эффекты:** нет. **Идемпотентность:** да.

### POST `/api/v1/oauth/token`

**Запрос:** form-data `OAuthCredentials`: `grant_type=client_credentials`, `client_id`, `client_secret`.

**Ответ:** `200 OK`, `OAuthTokenResponse`: `access_token`, `token_type`, `expires_at`.

**Ошибки:** 401 invalid/inactive service account or bad secret, 422 invalid form, 500. **Побочные эффекты:** выдача JWT. **Идемпотентность:** нет.

### GET `/api/v1/users/me`

**Авторизация:** Bearer. **Ответ:** `200 OK`, `UserResponse`.

**Ошибки:** 401, 404 if current user missing, 500. **Побочные эффекты:** нет.

### PATCH `/api/v1/users/me`

**Тело:** `UpdateUserDTO` / `UserUpdate`: nullable `username`, `full_name/fullName`, `avatar_url/avatarUrl` (точный casing зависит от DTO файла; часть DTO использует aliases).

**Ответ:** `200 OK`, `UserResponse`. **Ошибки:** 400 VO validation, 401, 404, 422, 500. **Побочные эффекты:** update `users`.

### POST `/api/v1/users/search`

**Запрос:** query pagination + filters `email`, `username`, `full_name`.

**Авторизация:** Bearer. **Ответ:** `200 OK`, `Page[UserResponse]`. **Ошибки:** 401, 422, 500. **Побочные эффекты:** нет.

### GET `/api/v1/users/{user_id}`

**Route:** `user_id: UUID`. **Авторизация:** Bearer. **Ответ:** `UserResponse`. **Ошибки:** 401, 404, 422, 500.

### GET `/api/v1/users/by-email/{email}`

**Route:** `email: EmailStr`. **Авторизация:** Bearer. **Ответ:** `UserResponse`. **Ошибки:** прямой `HTTPException(404)` if not found, 401, 422, 500.

### POST `/api/v1/roles`

**Авторизация:** `require_permissions(CREATE.code)` из `domain/permissions/roles.py`.

**Тело:** `CreateRoleDTO`: `name`, `code`, `description`, `permissions: set[PermissionGrant]`.

**Ответ:** `201 Created`, `RoleResponse`. **Ошибки:** 401, 403, 409 duplicate/invariant, 422, 500. **Побочные эффекты:** insert `roles`. **Идемпотентность:** нет.

### PATCH `/api/v1/roles/{role_id}`

**Route:** `role_id: UUID`. **Тело:** `UpdateRoleDTO`: nullable `name`, `code`, `description`.

**Авторизация:** `roles.update`. **Ответ:** `200 OK`, `RoleResponse`. **Ошибки:** 401/403/404/409/422/500. **Побочные эффекты:** update role.

### GET `/api/v1/roles`

**Авторизация:** `roles.read`. **Ответ:** заявлен `200 OK`, но handler — stub `...`; фактический response не определён кодом.

**Ошибки:** 401/403/500; дополнительные неизвестны. **Открытый вопрос:** endpoint заготовка или сломан.

### GET `/api/v1/roles/{role_id}`

**Route:** `role_id`. **Авторизация:** `roles.read`. **Ответ:** `200 OK`, `RoleResponse`. **Ошибки:** 401/403/404/422/500.

### DELETE `/api/v1/roles/{role_id}`

**Авторизация:** `roles.delete`. **Ответ:** `204 No Content`. **Ошибки:** 401/403/404/409 if default role, 422, 500. **Побочные эффекты:** delete/soft delete role depending repository implementation.

### POST `/api/v1/roles/{role_id}/permissions`

**Статус:** `200 OK`, но handler stub `...`, параметры/body не определены, auth не задана. Документируется как технический долг, не как рабочий контракт.

### DELETE `/api/v1/roles/{role_id}/permissions/{permission}`

**Статус:** `200 OK`, но handler stub `...`; path params есть в route, но handler их не принимает. Фактическое поведение требует проверки.

### GET `/api/v1/permissions`

**Авторизация:** `permissions.read`.

**Query:** pagination + `PermissionQueryParamFilters`: `resource`, `action`, `scopes`, `op`, `sort`, `search`.

**Ответ:** `200 OK`, `Page[PermissionResponse]`.

**Ошибки:** 401/403/422/500. **Побочные эффекты:** нет.

### POST `/api/v1/memberships`

**Авторизация:** `memberships.create`.

**Тело:** `CreateMembershipDTO`: `userId`, `organizationId`, `roles`, `expiresAt` по DTO aliases.

**Ответ:** `201 Created`, domain `Membership`. **Ошибки:** 401/403/404 user/org not found, 409 duplicate, 422, 500. **Побочные эффекты:** insert `memberships`.

### GET `/api/v1/memberships/{organization_id}/{user_id}`

**Route:** `organization_id`, `user_id`. **Авторизация:** `memberships.read`.

**Ответ:** `200 OK`, `Membership`. **Ошибки:** прямой `HTTPException(404)` if not found, 401/403/422/500. **Побочные эффекты:** нет.

### POST `/api/v1/invitations`

**Авторизация:** `invitations.invite`.

**Тело:** `InvitationCreate`: `email`, `grantedRoles`, `organizationId`.

**Ответ:** `201 Created`, `Invitation`. **Ошибки:** 401/403/404/409/422/500. **Побочные эффекты:** insert `invitations`, domain event `UserInvited`.

### POST `/api/v1/invitations/accept/{token}`

**Route:** `token`. **Авторизация:** нет.

**Тело:** `CreateUserDTO`: `password`, `fullName`, `username`.

**Ответ:** `201 Created`, `TokensResponse`.

**Ошибки:** 404 invalid/expired token по текущему flow, 409 user already exists, 422 `WeakPasswordError` или body validation, 500. **Побочные эффекты:** create user/membership, mark invitation used по условиям сервиса, issue JWT.

### DELETE `/api/v1/invitations/revoke/{invitation_id}`

**Route:** `invitation_id`. **Авторизация:** `invitations.delete`.

**Ответ:** `204 No Content`. **Ошибки:** 401/403/404/422/500. **Побочные эффекты:** revoke/delete invitation.

### POST `/api/v1/service-accounts`

**Авторизация:** не задана.

**Тело:** `CreateServiceAccountDTO`: `name`, `description`, `organization_id`, `roles`.

**Ответ:** `201 Created`, `ClientCredentials` с `client_secret` (секрет возвращается при создании).

**Ошибки:** 404 org/role not found, 403 role outside organization, 422, 500. **Побочные эффекты:** insert `service_accounts`. **Идемпотентность:** нет.

### POST `/api/v1/service-accounts/search`

**Авторизация:** не задана. **Запрос:** query/body pagination по dependency. **Ответ:** `200 OK`, `Page[ServiceAccountResponse]`. **Ошибки:** 422/500.

### GET `/api/v1/service-accounts/{service_account_id}`

**Авторизация:** не задана. **Route:** UUID. **Ответ:** `ServiceAccountResponse`. **Ошибки:** 404/422/500.

### PATCH `/api/v1/service-accounts/{service_account_id}`

**Авторизация:** не задана. **Тело:** `UpdateServiceAccountDTO`: nullable `name`, `description`, `roles`.

**Ответ:** `200 OK`, `ServiceAccountResponse`. **Ошибки:** 403/404/422/500. **Побочные эффекты:** update service account.

### DELETE `/api/v1/service-accounts/{service_account_id}`

**Авторизация:** не задана. **Ответ:** `204 No Content`. **Ошибки:** 404/422/500. **Побочные эффекты:** delete/deactivate service account depending CRUD implementation.
