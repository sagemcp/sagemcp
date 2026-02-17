# User-Level OAuth Tokens

SageMCP supports both **tenant-level** and **user-level** OAuth authentication:

- **Tenant-level OAuth** (default): Single OAuth credential shared by all users in a tenant
- **User-level OAuth**: Each user passes their own OAuth token per request

## HTTP POST Requests

Use the `X-User-OAuth-Token` custom header:

```bash
curl -X POST http://localhost:8000/api/v1/{tenant-slug}/connectors/{connector-id}/mcp \
  -H "X-User-OAuth-Token: <user-oauth-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## WebSocket Connections

Use the `auth/setUserToken` extension message:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/{tenant-slug}/connectors/{connector-id}/mcp');

ws.onopen = () => {
  // Set user token before initialize
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    method: 'auth/setUserToken',
    params: { token: '<user-oauth-token>' }
  }));

  // Then proceed with normal MCP flow
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: { protocolVersion: '2025-06-18' }  // also supports '2024-11-05'
  }));
};
```

## Token Priority

User token (if provided) → Tenant credential (fallback)

## Use Cases

- Multi-user SaaS apps where each user needs their own OAuth identity
- Testing with different user accounts
- Per-user access control and audit trails

> **Note**: User tokens are for external APIs (GitHub, Slack, etc.), separate from MCP protocol-level authentication.
