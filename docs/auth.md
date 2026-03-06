# Authentication & Authorization

All auth features are feature-flagged under `SAGEMCP_ENABLE_AUTH`. When disabled (the default), the platform runs without access control.

## Table of Contents

- [Enabling Auth](#enabling-auth)
- [Authentication Methods](#authentication-methods)
- [Roles and Permissions](#roles-and-permissions)
- [API Key Management](#api-key-management)
- [User Authentication (JWT)](#user-authentication-jwt)
- [Tenant Isolation](#tenant-isolation)
- [Global Tool Policies](#global-tool-policies)
- [Audit Logging](#audit-logging)
- [Field-Level Encryption](#field-level-encryption)
- [Environment Variables](#environment-variables)

---

## Enabling Auth

Add to your `.env`:

```bash
SAGEMCP_ENABLE_AUTH=true
SECRET_KEY=your-secret-key-min-16-chars  # required, min 16 chars
```

If `SECRET_KEY` is not set, an ephemeral key is generated on startup. Encrypted data will be unrecoverable after restart.

## Authentication Methods

All authenticated requests use the `Authorization: Bearer <token>` header. The platform tries JWT decode first (~0.1ms, no DB query), then falls back to API key lookup (bcrypt verify with SHA-256 LRU cache).

```
Authorization: Bearer eyJhbGciOiJIUzI1NiI...   # JWT access token
Authorization: Bearer smcp_pa_abc123...          # API key
```

For WebSocket connections, pass credentials via:
- Query parameter: `?api_key=<token>`
- Or the `Authorization` header (if your client supports it)

## Roles and Permissions

4 roles with 18 fine-grained permissions:

| Permission | platform_admin | tenant_admin | tenant_member | tenant_viewer |
|------------|:-:|:-:|:-:|:-:|
| `tenant_create` | x | x | | |
| `tenant_read` | x | x | | |
| `tenant_update` | x | x | | |
| `tenant_delete` | x | x | | |
| `connector_create` | x | x | | |
| `connector_read` | x | x | x | x |
| `connector_update` | x | x | | |
| `connector_delete` | x | x | | |
| `tool_call` | x | x | x | |
| `tool_configure` | x | x | | |
| `process_manage` | x | x | | |
| `stats_view_own` | x | x | x | x |
| `stats_view_global` | x | | | |
| `audit_view_own` | x | x | | |
| `audit_view_global` | x | | | |
| `key_manage` | x | x | | |
| `user_manage` | x | x | | |
| `policy_manage` | x | x | | |

API key scopes map to roles: `platform_admin` -> platform_admin, `tenant_admin` -> tenant_admin, `tenant_user` -> tenant_member.

Source: [`src/sage_mcp/security/permissions.py`](../src/sage_mcp/security/permissions.py)

## API Key Management

API keys use scope-based prefixes for quick identification:

| Scope | Prefix | Access |
|-------|--------|--------|
| `platform_admin` | `smcp_pa_` | Full platform access |
| `tenant_admin` | `smcp_ta_` | Full access to assigned tenant |
| `tenant_user` | `smcp_tu_` | Read + tool execution on assigned tenant |

### Bootstrap

On first startup with no API keys in the database:

**Option A:** Set `SAGEMCP_BOOTSTRAP_ADMIN_KEY` in `.env` to pre-create a platform admin key.

**Option B:** Register the first user (see [User Authentication](#user-authentication-jwt) below).

### Endpoints

```
POST   /auth/keys          # Create API key (platform_admin)
GET    /auth/keys          # List API keys (platform_admin)
DELETE /auth/keys/{key_id} # Revoke API key (platform_admin)
POST   /auth/verify        # Verify current credentials
```

### Create a key

```bash
curl -X POST http://localhost:8000/auth/keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI pipeline",
    "scope": "tenant_admin",
    "tenant_id": "uuid-of-tenant"
  }'
# Response includes the plaintext key (shown only once):
# { "key": "smcp_ta_abc123...", ... }
```

## User Authentication (JWT)

JWT access tokens (default 30 min) + refresh tokens (default 7 days) with rotation.

### Endpoints

```
POST /auth/register   # Create user (open when 0 users, then requires platform_admin)
POST /auth/login      # Email + password -> access_token + refresh_token
POST /auth/refresh    # Rotate refresh token, get new token pair
POST /auth/logout     # Revoke refresh token
```

### First user bootstrap

When no users exist, `POST /auth/register` is open to anyone. The first registered user should then be assigned a platform_admin role via tenant membership.

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "secure-password-here"}'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "secure-password-here"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiI...",
  "refresh_token": "eyJhbGciOiJIUzI1NiI...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Refresh

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiI..."}'
```

The old refresh token is revoked and a new pair is issued.

### Logout

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiI..."}'
```

## Tenant Isolation

When auth is enabled, access is scoped:

- **platform_admin** keys/tokens can access all tenants.
- **tenant_admin** and **tenant_user** keys are bound to a specific tenant. They cannot access other tenants' connectors, MCP endpoints, or audit logs.
- WebSocket MCP connections verify the caller's tenant scope against the URL's tenant slug.
- Process management operations check tenant ownership.

## Global Tool Policies

Platform admins can create rules that block or warn on tools across all tenants. Policies use glob patterns matched against tool names.

Policies are loaded into an in-memory cache at startup and refreshed on CRUD operations. Tool calls check the cache -- zero DB queries on the hot path.

### Endpoints

```
GET    /api/v1/admin/policies/tools              # List all policies
POST   /api/v1/admin/policies/tools              # Create policy
PUT    /api/v1/admin/policies/tools/{policy_id}  # Update policy
DELETE /api/v1/admin/policies/tools/{policy_id}  # Delete policy
```

### Create a policy

```bash
# Block all "delete" tools across the platform
curl -X POST http://localhost:8000/api/v1/admin/policies/tools \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name_pattern": "*_delete_*",
    "action": "block",
    "reason": "Destructive operations disabled in production"
  }'
```

Policy actions: `block` (reject the tool call) or `warn` (log a warning, allow execution).

The `connector_type` field optionally scopes the policy to a specific connector (e.g., `"github"`).

## Audit Logging

All state-changing operations are recorded asynchronously (fire-and-forget, does not block the request). Tracked events include tenant CRUD, connector CRUD, tool toggles, and API key management.

### Endpoints

```
GET /api/v1/admin/audit                      # Global audit log (platform_admin)
GET /api/v1/admin/tenants/{slug}/audit       # Tenant-scoped audit log (tenant_admin+)
```

Both endpoints support filtering and pagination:

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | Filter by action (e.g., `tenant.create`) |
| `actor_id` | string | Filter by who performed the action |
| `tenant_id` | string | Filter by tenant (global endpoint only) |
| `start` | datetime | Start of time range |
| `end` | datetime | End of time range |
| `limit` | int | Page size (max 200, default 50) |
| `offset` | int | Pagination offset |

### Example

```bash
curl "http://localhost:8000/api/v1/admin/audit?action=connector.create&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Field-Level Encryption

Sensitive database columns (OAuth tokens, client secrets, connector configs) are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256). The encryption key is derived from `SECRET_KEY` via PBKDF2-SHA256 with 480,000 iterations.

Encryption/decryption is transparent -- values are encrypted on write and decrypted on read via SQLAlchemy column-level type decorators. No application code changes needed when reading or writing these fields.

If `SECRET_KEY` changes, existing encrypted values become unrecoverable.

## Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `SECRET_KEY` | Yes | -- | Encryption + JWT signing key (min 16 chars) |
| `SAGEMCP_ENABLE_AUTH` | No | `false` | Enable all auth features |
| `SAGEMCP_BOOTSTRAP_ADMIN_KEY` | No | -- | Pre-set platform admin API key on first startup |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | JWT refresh token lifetime in days |

Source files:
- Auth middleware: [`src/sage_mcp/security/auth.py`](../src/sage_mcp/security/auth.py)
- Permissions: [`src/sage_mcp/security/permissions.py`](../src/sage_mcp/security/permissions.py)
- Auth endpoints: [`src/sage_mcp/api/auth.py`](../src/sage_mcp/api/auth.py)
- Tool policies: [`src/sage_mcp/api/admin_policies.py`](../src/sage_mcp/api/admin_policies.py)
- Audit log: [`src/sage_mcp/api/admin_audit.py`](../src/sage_mcp/api/admin_audit.py)
