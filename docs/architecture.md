# SageMCP Architecture

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        CD[Claude Desktop]
        WEB[Web Browser]
    end

    subgraph "SageMCP Platform"
        subgraph "Frontend - React App :3001"
            UI[React UI]
            PAGES[Pages: Dashboard, Tenants, Connectors]
            COMP[Components: Modals, Forms]
        end

        subgraph "Backend - FastAPI :8000"
            API[FastAPI Application]

            subgraph "Middleware"
                RATE_LIM["Rate Limiter
Token Bucket · 100 RPM"]
                CORS_MW["CORS / Origin
Validation"]
                CT_VAL["Content-Type
Validation"]
            end

            subgraph "API Routes"
                ADMIN["Admin API
/api/v1/admin/*"]
                OAUTH["OAuth API
/api/v1/oauth/*"]
                MCP_ROUTE["MCP API
/api/v1/SLUG/connectors/ID/mcp"]
            end

            subgraph "MCP Core"
                POOL["ServerPool
LRU · 5000 max · 30min TTL"]
                SESS_MGR["SessionManager
Mcp-Session-Id · 10/key"]
                MCP_TRANSPORT["Transport
HTTP POST · WebSocket · SSE"]
                EBUF["EventBuffer
Ring Buffer · 100 events"]
            end

            subgraph "Connector System"
                REGISTRY[Connector Registry]

                subgraph "Native Plugins"
                    subgraph "Code & VCS"
                        GH["GitHub · 24 tools"]
                        GL["GitLab · 22 tools"]
                        BB["Bitbucket · 19 tools"]
                    end
                    subgraph "Project Mgmt"
                        JIRA["Jira · 20 tools"]
                        LINEAR["Linear · 18 tools"]
                        CONFL["Confluence · 16 tools"]
                    end
                    subgraph "Communication"
                        SLACK["Slack · 11 tools"]
                        DISCORD["Discord · 15 tools"]
                        TEAMS["Teams · 13 tools"]
                    end
                    subgraph "Email"
                        GMAIL["Gmail · 14 tools"]
                        OUTLOOK["Outlook · 14 tools"]
                    end
                    subgraph "Docs & Productivity"
                        GDOCS["Google Docs · 10 tools"]
                        GSHEETS["Google Sheets · 14 tools"]
                        GSLIDES["Google Slides · 11 tools"]
                        NOTION["Notion · 10 tools"]
                        EXCEL["Excel · 14 tools"]
                        PPTX["PowerPoint · 10 tools"]
                    end
                    ZOOM["Zoom · 12 tools"]
                    subgraph "AI Coding Tools"
                        COPILOT["Copilot · 19 tools"]
                        CLAUDE_CODE["Claude Code · 18 tools"]
                        CODEX["Codex · 16 tools"]
                        CURSOR_CONN["Cursor · 18 tools"]
                        WINDSURF["Windsurf · 11 tools"]
                    end
                end

                subgraph "External MCP Servers"
                    PROC_MGR["MCPProcessManager
Health checks · Auto-restart"]
                    GEN_CONN["GenericMCPConnector
stdio · JSON-RPC"]
                end
            end

            subgraph "Observability"
                PROM_EP["Prometheus /metrics
11 metrics"]
                STRUCT_LOG["Structured JSON Logs"]
                HEALTH_EP["Health Probes
/health/live · ready · startup"]
            end

            subgraph "Data Layer"
                ORM[SQLAlchemy ORM]
                DB_MGR[Database Manager]
            end
        end

        subgraph "Database"
            DB[("PostgreSQL /
Supabase")]

            subgraph "Tables"
                T_TENANT[Tenants]
                T_CONN[Connectors]
                T_OAUTH[OAuth Credentials]
                T_CONFIG[OAuth Configs]
                T_TOOL_STATE[ConnectorToolStates]
            end
        end
    end

    subgraph "External Services"
        GITHUB_API[GitHub API]
        GITLAB_API[GitLab API]
        BB_API[Bitbucket API]
        SLACK_API[Slack API]
        DISCORD_API[Discord API]
        TEAMS_API[MS Teams API]
        JIRA_API[Jira API]
        LINEAR_API[Linear API]
        CONFL_API[Confluence API]
        GOOGLE_API[Google APIs]
        MS_GRAPH_API[MS Graph API]
        NOTION_API[Notion API]
        ZOOM_API[Zoom API]
    end

    subgraph "External MCP Runtimes"
        EXT_PY["Python MCP Server"]
        EXT_NODE["Node.js MCP Server"]
        EXT_GO["Go MCP Server"]
    end

    %% Client connections
    CD -->|"HTTP POST / WebSocket"| MCP_ROUTE
    WEB -->|HTTP| UI

    %% Frontend to Backend
    UI -->|REST API| ADMIN
    UI -->|REST API| OAUTH

    %% Middleware chain
    MCP_ROUTE --> RATE_LIM
    RATE_LIM --> CT_VAL
    CT_VAL --> CORS_MW
    CORS_MW --> MCP_TRANSPORT

    %% MCP Core flow
    MCP_TRANSPORT --> POOL
    POOL --> SESS_MGR
    SESS_MGR -->|"Get/Create Server"| REGISTRY
    MCP_TRANSPORT -->|"SSE replay"| EBUF

    %% Connector routing
    REGISTRY -->|"runtime=native"| GH
    REGISTRY -->|"runtime=native"| GL
    REGISTRY -->|"runtime=native"| BB
    REGISTRY -->|"runtime=native"| JIRA
    REGISTRY -->|"runtime=native"| LINEAR
    REGISTRY -->|"runtime=native"| CONFL
    REGISTRY -->|"runtime=native"| SLACK
    REGISTRY -->|"runtime=native"| DISCORD
    REGISTRY -->|"runtime=native"| TEAMS
    REGISTRY -->|"runtime=native"| GMAIL
    REGISTRY -->|"runtime=native"| OUTLOOK
    REGISTRY -->|"runtime=native"| GDOCS
    REGISTRY -->|"runtime=native"| GSHEETS
    REGISTRY -->|"runtime=native"| GSLIDES
    REGISTRY -->|"runtime=native"| NOTION
    REGISTRY -->|"runtime=native"| EXCEL
    REGISTRY -->|"runtime=native"| PPTX
    REGISTRY -->|"runtime=native"| ZOOM
    REGISTRY -->|"runtime=native"| COPILOT
    REGISTRY -->|"runtime=native"| CLAUDE_CODE
    REGISTRY -->|"runtime=native"| CODEX
    REGISTRY -->|"runtime=native"| CURSOR_CONN
    REGISTRY -->|"runtime=native"| WINDSURF
    REGISTRY -->|"runtime=external"| PROC_MGR
    PROC_MGR --> GEN_CONN

    %% API routing
    ADMIN -->|Manage| ORM
    OAUTH -->|Auth Flow| ORM

    %% Database connections
    ORM -->|Async Queries| DB_MGR
    DB_MGR -->|Connection Pool| DB

    %% External API calls
    GH -->|REST API| GITHUB_API
    GL -->|REST API| GITLAB_API
    BB -->|REST API| BB_API
    JIRA -->|REST API| JIRA_API
    LINEAR -->|GraphQL| LINEAR_API
    CONFL -->|REST API| CONFL_API
    SLACK -->|REST API| SLACK_API
    DISCORD -->|REST API| DISCORD_API
    TEAMS -->|Graph API| TEAMS_API
    GMAIL -->|REST API| GOOGLE_API
    OUTLOOK -->|Graph API| MS_GRAPH_API
    GDOCS -->|REST API| GOOGLE_API
    GSHEETS -->|REST API| GOOGLE_API
    GSLIDES -->|REST API| GOOGLE_API
    NOTION -->|REST API| NOTION_API
    EXCEL -->|Graph API| MS_GRAPH_API
    PPTX -->|Graph API| MS_GRAPH_API
    ZOOM -->|REST API| ZOOM_API

    %% External MCP runtimes
    GEN_CONN -->|stdio| EXT_PY
    GEN_CONN -->|stdio| EXT_NODE
    GEN_CONN -->|stdio| EXT_GO

    style CD fill:#e1f5ff
    style WEB fill:#e1f5ff
    style UI fill:#fff3e0
    style API fill:#f3e5f5
    style POOL fill:#e8f5e9
    style SESS_MGR fill:#e8f5e9
    style MCP_TRANSPORT fill:#e8f5e9
    style EBUF fill:#e8f5e9
    style REGISTRY fill:#e8f5e9
    style PROC_MGR fill:#e8f5e9
    style GEN_CONN fill:#e8f5e9
    style DB fill:#fce4ec
    style RATE_LIM fill:#fff9c4
    style CORS_MW fill:#fff9c4
    style CT_VAL fill:#fff9c4
    style PROM_EP fill:#f3e5f5
    style HEALTH_EP fill:#f3e5f5
```

## Multi-Tenant Architecture

```mermaid
graph TB
    subgraph "Shared Infrastructure"
        POOL["ServerPool
LRU · 5000 max · 30min TTL"]
    end

    subgraph "Tenant 1: acme-corp"
        T1["Tenant: acme-corp
ID: uuid-1
Rate Limit: 100 RPM"]
        T1_CONN1["Connector: GitHub
Enabled"]
        T1_CONN2["Connector: Slack
Enabled"]
        T1_OAUTH1["OAuth: GitHub
access_token"]
        T1_OAUTH2["OAuth: Slack
access_token"]

        T1 --> T1_CONN1
        T1 --> T1_CONN2
        T1 --> T1_OAUTH1
        T1 --> T1_OAUTH2
        T1_CONN1 -.uses.-> T1_OAUTH1
        T1_CONN2 -.uses.-> T1_OAUTH2
    end

    subgraph "Tenant 2: startup-inc"
        T2["Tenant: startup-inc
ID: uuid-2
Rate Limit: 100 RPM"]
        T2_CONN1["Connector: Jira
Enabled"]
        T2_CONN2["Connector: Zoom
Enabled"]
        T2_OAUTH1["OAuth: Jira
access_token"]
        T2_OAUTH2["OAuth: Zoom
access_token"]

        T2 --> T2_CONN1
        T2 --> T2_CONN2
        T2 --> T2_OAUTH1
        T2 --> T2_OAUTH2
        T2_CONN1 -.uses.-> T2_OAUTH1
        T2_CONN2 -.uses.-> T2_OAUTH2
    end

    CD1["Claude Desktop
Tenant 1"]
    CD2["Claude Desktop
Tenant 2"]

    CD1 -->|"HTTP POST: /api/v1/acme-corp/connectors/ID/mcp"| T1
    CD2 -->|"HTTP POST: /api/v1/startup-inc/connectors/ID/mcp"| T2

    T1_CONN1 -->|"key: acme-corp:conn-id"| POOL
    T2_CONN1 -->|"key: startup-inc:conn-id"| POOL

    style T1 fill:#e3f2fd
    style T2 fill:#f3e5f5
    style CD1 fill:#e1f5ff
    style CD2 fill:#e1f5ff
    style POOL fill:#e8f5e9
```

## OAuth Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant SageMCP
    participant Provider as OAuth Provider (GitHub/Slack/etc)
    participant API as External API

    User->>Frontend: Click "Connect GitHub"
    Frontend->>SageMCP: POST /api/v1/oauth/github/auth
    SageMCP->>SageMCP: Generate state token
    SageMCP->>Frontend: Redirect URL with state
    Frontend->>Provider: Redirect to OAuth authorization
    Provider->>User: Show authorization page
    User->>Provider: Approve permissions
    Provider->>SageMCP: Redirect with auth code
    SageMCP->>Provider: Exchange code for token
    Provider->>SageMCP: Return access_token & refresh_token
    SageMCP->>SageMCP: Store OAuthCredential in DB
    SageMCP->>Frontend: Redirect to /oauth/success
    Frontend->>User: Show success message

    Note over SageMCP,API: Later: MCP Tool Execution
    User->>SageMCP: Execute tool via MCP
    SageMCP->>SageMCP: Load OAuth credential
    SageMCP->>API: Call API with access_token
    API->>SageMCP: Return data
    SageMCP->>User: Return MCP response
```

## MCP Tool Execution Flow

```mermaid
sequenceDiagram
    participant Client as Claude Desktop
    participant MW as Middleware
    participant Transport as MCP Transport
    participant Pool as ServerPool
    participant Session as SessionManager
    participant Registry as Connector Registry
    participant Connector as Connector Plugin
    participant DB as Database
    participant API as External API

    Note over Client,MW: HTTP POST /api/v1/SLUG/connectors/ID/mcp
    Client->>MW: POST with Content-Type: application/json
    MW->>MW: Rate limit check (token bucket)
    MW->>MW: Content-Type validation
    MW->>MW: Origin header validation
    MW->>Transport: Forward JSON-RPC request

    Note over Transport,Session: Initialize (first request)
    Transport->>Transport: Parse JSON-RPC (single or batch)
    Transport->>Pool: get_or_create("SLUG:ID")
    Pool-->>Transport: Cache HIT (existing server)
    Pool->>DB: Cache MISS → Load Tenant & Connector
    DB->>Pool: Return config
    Pool->>Registry: Create MCPServer
    Registry->>Pool: Return server instance
    Transport->>Session: create_session(SLUG, ID, server)
    Session->>Transport: Return session_id
    Transport->>Transport: Negotiate protocol version (2025-06-18 / 2024-11-05)
    Transport->>Client: Response + Mcp-Session-Id header

    Note over Client,API: Subsequent requests (tools/list, tools/call)
    Client->>MW: POST + Mcp-Session-Id header
    MW->>Transport: Forward
    Transport->>Session: get_session(session_id)
    Session->>Transport: Return server instance

    Client->>Transport: tools/list
    Transport->>Registry: Get connector by type
    Registry->>Connector: get_tools()
    Connector->>Transport: Return tool definitions
    Transport->>Client: Tool list

    Client->>Transport: call_tool("github_list_repositories", args)
    Transport->>Registry: Get connector
    Registry->>Connector: execute_tool(name, args, oauth)
    Connector->>DB: Load OAuth credential
    DB->>Connector: access_token
    Connector->>API: GET /user/repos Authorization: Bearer TOKEN
    API->>Connector: Repository list
    Connector->>Transport: Format as TextContent
    Transport->>Client: MCP response with data
```

## Database Schema

```mermaid
erDiagram
    TENANT ||--o{ CONNECTOR : has
    TENANT ||--o{ OAUTH_CREDENTIAL : has
    TENANT ||--o{ OAUTH_CONFIG : has
    TENANT ||--o{ AUDIT_LOG : has
    CONNECTOR ||--o{ CONNECTOR_TOOL_STATE : has
    USER ||--o{ REFRESH_TOKEN : has
    USER ||--o{ USER_TENANT_MEMBERSHIP : has
    TENANT ||--o{ USER_TENANT_MEMBERSHIP : has
    TENANT ||--o{ API_KEY : scoped_to

    TENANT {
        uuid id PK
        string slug UK
        string name
        string description
        boolean is_active
        string contact_email
        json settings
        datetime created_at
        datetime updated_at
    }

    CONNECTOR {
        uuid id PK
        uuid tenant_id FK
        enum connector_type
        string name
        string description
        boolean is_enabled
        json configuration
        datetime created_at
        datetime updated_at
    }

    OAUTH_CREDENTIAL {
        uuid id PK
        uuid tenant_id FK
        string provider
        string provider_user_id
        string provider_username
        text access_token "encrypted"
        text refresh_token "encrypted"
        datetime expires_at
        string scopes
        string provider_data
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    OAUTH_CONFIG {
        uuid id PK
        uuid tenant_id FK
        string provider
        string client_id
        string client_secret "encrypted"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    CONNECTOR_TOOL_STATE {
        uuid id PK
        uuid connector_id FK
        string tool_name
        boolean is_enabled
        datetime created_at
        datetime updated_at
    }

    USER {
        uuid id PK
        string email UK
        string display_name
        string password_hash
        enum auth_provider
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    REFRESH_TOKEN {
        uuid id PK
        uuid user_id FK
        string token_hash
        boolean revoked
        datetime expires_at
        datetime created_at
    }

    USER_TENANT_MEMBERSHIP {
        uuid id PK
        uuid user_id FK
        uuid tenant_id FK
        enum role
        datetime created_at
    }

    API_KEY {
        uuid id PK
        string name
        string key_prefix
        string key_hash
        enum scope
        uuid tenant_id FK "nullable"
        boolean is_active
        datetime expires_at
        datetime created_at
    }

    AUDIT_LOG {
        uuid id PK
        datetime timestamp
        string actor_id
        string actor_type
        string action
        string resource_type
        string resource_id
        uuid tenant_id FK "nullable"
        json details
        string ip_address
        string user_agent
    }

    GLOBAL_TOOL_POLICY {
        uuid id PK
        string tool_name_pattern
        enum action
        string reason
        string created_by
        string connector_type
        boolean is_active
        datetime created_at
        datetime updated_at
    }
```

## Connector Plugin Architecture

```mermaid
graph TB
    subgraph "Connector Registry"
        REG["ConnectorRegistry
Singleton · async"]
        REG_MAP{Connector Map}
        ROUTING{"Route by
runtime_type"}

        REG --> REG_MAP
        REG --> ROUTING
    end

    subgraph "Base Class"
        BASE["BaseConnector
Abstract Class"]

        BASE_PROPS["Properties:
- name
- display_name
- requires_oauth"]
        BASE_METHODS["Methods:
- get_tools
- get_resources
- execute_tool
- read_resource
- validate_oauth"]

        BASE --> BASE_PROPS
        BASE --> BASE_METHODS
    end

    subgraph "Native Connector Plugins (23 connectors · 340 tools)"
        subgraph "Code & VCS"
            GH_CONN["GitHubConnector · 24 tools"]
            GL_CONN["GitLabConnector · 22 tools"]
            BB_CONN["BitbucketConnector · 19 tools"]
        end
        subgraph "Project Management"
            JIRA_CONN["JiraConnector · 20 tools"]
            LINEAR_CONN["LinearConnector · 18 tools"]
            CONFL_CONN["ConfluenceConnector · 16 tools"]
        end
        subgraph "Communication"
            SLACK_CONN["SlackConnector · 11 tools"]
            DISCORD_CONN["DiscordConnector · 15 tools"]
            TEAMS_CONN["TeamsConnector · 13 tools"]
        end
        subgraph "Email"
            GMAIL_CONN["GmailConnector · 14 tools"]
            OUTLOOK_CONN["OutlookConnector · 14 tools"]
        end
        subgraph "Docs & Productivity"
            GDOCS_CONN["GoogleDocsConnector · 10 tools"]
            GSHEETS_CONN["GoogleSheetsConnector · 14 tools"]
            GSLIDES_CONN["GoogleSlidesConnector · 11 tools"]
            NOTION_CONN["NotionConnector · 10 tools"]
            EXCEL_CONN["ExcelConnector · 14 tools"]
            PPTX_CONN["PowerPointConnector · 10 tools"]
        end
        ZOOM_CONN["ZoomConnector · 12 tools"]
    end

    subgraph "Shared Infrastructure"
        PAGINATION["Pagination
offset · cursor · link · OData"]
        RETRY["Retry
Exponential backoff · jitter"]
        GRAPHQL["GraphQL Client
Relay pagination"]
        EXCEPTIONS["Structured Exceptions
Auth · RateLimit · API · Timeout"]
    end

    subgraph "External MCP Server Path"
        PROC_MGR["MCPProcessManager
Health checks · Auto-restart
Max 3 retries"]
        GEN_CONN["GenericMCPConnector
stdio · JSON-RPC 2.0
30s timeout"]

        subgraph "External Runtimes"
            EXT_PY["Python MCP Server"]
            EXT_NODE["Node.js MCP Server"]
            EXT_GO["Go MCP Server"]
        end

        PROC_MGR --> GEN_CONN
        GEN_CONN -->|stdio| EXT_PY
        GEN_CONN -->|stdio| EXT_NODE
        GEN_CONN -->|stdio| EXT_GO
    end

    ROUTING -->|"runtime=native"| REG_MAP
    ROUTING -->|"runtime=external_*"| PROC_MGR

    REG_MAP -->|"github"| GH_CONN
    REG_MAP -->|"gitlab"| GL_CONN
    REG_MAP -->|"bitbucket"| BB_CONN
    REG_MAP -->|"jira"| JIRA_CONN
    REG_MAP -->|"linear"| LINEAR_CONN
    REG_MAP -->|"confluence"| CONFL_CONN
    REG_MAP -->|"slack"| SLACK_CONN
    REG_MAP -->|"discord"| DISCORD_CONN
    REG_MAP -->|"teams"| TEAMS_CONN
    REG_MAP -->|"gmail"| GMAIL_CONN
    REG_MAP -->|"outlook"| OUTLOOK_CONN
    REG_MAP -->|"google_docs"| GDOCS_CONN
    REG_MAP -->|"google_sheets"| GSHEETS_CONN
    REG_MAP -->|"google_slides"| GSLIDES_CONN
    REG_MAP -->|"notion"| NOTION_CONN
    REG_MAP -->|"excel"| EXCEL_CONN
    REG_MAP -->|"powerpoint"| PPTX_CONN
    REG_MAP -->|"zoom"| ZOOM_CONN

    BASE -.->|inherits| GH_CONN
    BASE -.->|inherits| GL_CONN
    BASE -.->|inherits| BB_CONN
    BASE -.->|inherits| JIRA_CONN
    BASE -.->|inherits| LINEAR_CONN
    BASE -.->|inherits| CONFL_CONN
    BASE -.->|inherits| SLACK_CONN
    BASE -.->|inherits| DISCORD_CONN
    BASE -.->|inherits| TEAMS_CONN
    BASE -.->|inherits| GMAIL_CONN
    BASE -.->|inherits| OUTLOOK_CONN
    BASE -.->|inherits| GDOCS_CONN
    BASE -.->|inherits| GSHEETS_CONN
    BASE -.->|inherits| GSLIDES_CONN
    BASE -.->|inherits| NOTION_CONN
    BASE -.->|inherits| EXCEL_CONN
    BASE -.->|inherits| PPTX_CONN
    BASE -.->|inherits| ZOOM_CONN

    style REG fill:#e8f5e9
    style ROUTING fill:#e8f5e9
    style BASE fill:#fff3e0
    style GH_CONN fill:#e3f2fd
    style GL_CONN fill:#e3f2fd
    style BB_CONN fill:#e3f2fd
    style JIRA_CONN fill:#e3f2fd
    style LINEAR_CONN fill:#e3f2fd
    style CONFL_CONN fill:#e3f2fd
    style SLACK_CONN fill:#e3f2fd
    style DISCORD_CONN fill:#e3f2fd
    style TEAMS_CONN fill:#e3f2fd
    style GMAIL_CONN fill:#e3f2fd
    style OUTLOOK_CONN fill:#e3f2fd
    style GDOCS_CONN fill:#e3f2fd
    style GSHEETS_CONN fill:#e3f2fd
    style GSLIDES_CONN fill:#e3f2fd
    style NOTION_CONN fill:#e3f2fd
    style EXCEL_CONN fill:#e3f2fd
    style PPTX_CONN fill:#e3f2fd
    style ZOOM_CONN fill:#e3f2fd
    style PROC_MGR fill:#fff9c4
    style GEN_CONN fill:#fff9c4
    style PAGINATION fill:#f3e5f5
    style RETRY fill:#f3e5f5
    style GRAPHQL fill:#f3e5f5
    style EXCEPTIONS fill:#f3e5f5
```

## Request Flow: Creating and Using a Connector

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Admin User
    participant UI as Web UI
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Provider as OAuth Provider
    participant Claude as Claude Desktop
    participant Connector as Connector Plugin
    participant ExtAPI as External API

    Note over Admin,DB: Step 1: Create Tenant
    Admin->>UI: Create tenant "acme-corp"
    UI->>API: POST /api/v1/admin/tenants
    API->>DB: INSERT INTO tenants
    DB->>API: Tenant created
    API->>UI: Return tenant data

    Note over Admin,Provider: Step 2: Setup OAuth
    Admin->>UI: Configure GitHub OAuth
    UI->>API: POST /api/v1/oauth/github/auth
    API->>Provider: Redirect to authorization
    Provider->>Admin: Show authorization page
    Admin->>Provider: Approve
    Provider->>API: Callback with auth code
    API->>Provider: Exchange code for token
    Provider->>API: Return access_token
    API->>DB: INSERT INTO oauth_credentials
    API->>UI: OAuth success

    Note over Admin,DB: Step 3: Create Connector
    Admin->>UI: Add GitHub connector
    UI->>API: POST /api/v1/admin/tenants/ID/connectors
    API->>DB: INSERT INTO connectors
    DB->>API: Connector created
    API->>UI: Connector ready

    Note over Claude,ExtAPI: Step 4: Use MCP Tools
    Claude->>API: WebSocket connect /api/v1/acme-corp/connectors/ID/mcp
    API->>DB: Load tenant, connector, oauth
    DB->>API: Return configuration
    API->>Claude: WebSocket connected

    Claude->>API: call_tool("github_list_repositories")
    API->>Connector: execute_tool()
    Connector->>DB: Get OAuth credential
    DB->>Connector: access_token
    Connector->>ExtAPI: GET /user/repos Bearer TOKEN
    ExtAPI->>Connector: Repository list JSON
    Connector->>API: Format response
    API->>Claude: MCP TextContent response
```

## MCP Request Lifecycle (v2 — Streamable HTTP)

```mermaid
sequenceDiagram
    autonumber
    participant Client as Claude Desktop
    participant RL as Rate Limiter
    participant CT as Content-Type Check
    participant OV as Origin Validator
    participant TP as Transport
    participant Pool as ServerPool
    participant Sess as SessionManager
    participant Buf as EventBuffer
    participant Conn as Connector

    Note over Client,RL: HTTP POST /api/v1/{slug}/connectors/{id}/mcp

    Client->>RL: POST JSON-RPC (Content-Type: application/json)
    RL->>RL: Token bucket check for tenant slug
    alt Rate limit exceeded
        RL-->>Client: 429 Too Many Requests + Retry-After
    end
    RL->>CT: Forward request
    CT->>CT: Validate Content-Type: application/json
    alt Invalid Content-Type
        CT-->>Client: 415 Unsupported Media Type
    end
    CT->>OV: Forward request
    OV->>OV: Validate Origin header against MCP_ALLOWED_ORIGINS
    alt Origin rejected
        OV-->>Client: 403 Forbidden
    end
    OV->>TP: Forward validated request

    TP->>TP: Parse JSON-RPC (single request or batch array)

    alt method = "initialize"
        TP->>Pool: get_or_create(slug:connector_id)
        Pool-->>TP: MCPServer (cache hit or new)
        TP->>Sess: create_session(slug, connector_id, server)
        Sess-->>TP: session_id (UUID4 hex)
        TP->>TP: Negotiate version (2025-06-18 preferred, 2024-11-05 fallback)
        TP->>Buf: create_buffer(session_id, capacity=100)
        TP-->>Client: initialize result + Mcp-Session-Id header
    else method = "tools/list" | "tools/call"
        Client->>TP: Mcp-Session-Id header
        TP->>Sess: get_session(session_id)
        Sess-->>TP: MCPServer instance
        TP->>Conn: execute via connector
        Conn-->>TP: Result
        TP->>Buf: append(SSEEvent)
        TP-->>Client: JSON-RPC response
    else method = "notifications/*"
        TP->>TP: Process notification (no response)
    end
```

## Technology Stack

```mermaid
graph LR
    subgraph "Frontend Stack"
        REACT[React 18]
        TS[TypeScript]
        VITE[Vite]
        RR[React Router]
        TAILWIND[Tailwind CSS]

        REACT --> TS
        REACT --> VITE
        REACT --> RR
        REACT --> TAILWIND
    end

    subgraph "Backend Stack"
        FASTAPI[FastAPI]
        PYTHON[Python 3.11+]
        SA[SQLAlchemy 2.0]
        PYDANTIC[Pydantic v2]
        MCP_SDK[MCP SDK]
        HTTPX[HTTPX]
        PROM_CLIENT[prometheus-client]

        FASTAPI --> PYTHON
        FASTAPI --> SA
        FASTAPI --> PYDANTIC
        FASTAPI --> MCP_SDK
        FASTAPI --> HTTPX
        FASTAPI --> PROM_CLIENT
    end

    subgraph "Database Stack"
        POSTGRES[PostgreSQL 15]
        SUPABASE[Supabase]
        ASYNCPG[AsyncPG]

        POSTGRES -.alternative.-> SUPABASE
        SA --> ASYNCPG
        ASYNCPG --> POSTGRES
        ASYNCPG --> SUPABASE
    end

    subgraph "DevOps Stack"
        DOCKER[Docker]
        DC[Docker Compose]
        K8S[Kubernetes]
        HELM[Helm Charts]

        DOCKER --> DC
        K8S --> HELM
    end

    subgraph "Testing Stack"
        PYTEST[Pytest]
        PYTEST_ASYNC[pytest-asyncio]
        MOCK[unittest.mock]

        PYTEST --> PYTEST_ASYNC
        PYTEST --> MOCK
    end

    style REACT fill:#61dafb
    style FASTAPI fill:#009688
    style POSTGRES fill:#336791
    style DOCKER fill:#2496ed
    style PYTEST fill:#0a9edc
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            ING["Ingress Controller
NGINX/Traefik"]
        end

        subgraph "Application Pods"
            FE1["Frontend Pod 1
React:3001"]
            FE2["Frontend Pod 2
React:3001"]
            BE1["Backend Pod 1
FastAPI:8000
liveness: /health/live
readiness: /health/ready
startup: /health/startup"]
            BE2["Backend Pod 2
FastAPI:8000
liveness: /health/live
readiness: /health/ready
startup: /health/startup"]
            BE3["Backend Pod 3
FastAPI:8000
prometheus.io/scrape: true
prometheus.io/path: /metrics"]
        end

        subgraph "Services"
            FE_SVC["Frontend Service
ClusterIP"]
            BE_SVC["Backend Service
ClusterIP"]
        end

        subgraph "Configuration"
            CM["ConfigMap
- API URLs
- Feature flags"]
            SEC["Secrets
- OAuth credentials
- DB password
- SECRET_KEY"]
        end
    end

    subgraph "Managed Services"
        DB_MANAGED["Managed PostgreSQL
or Supabase"]
        REDIS["Redis Cache
Optional"]
    end

    USERS[Users/Clients]

    USERS -->|HTTPS| ING
    ING -->|Route /| FE_SVC
    ING -->|Route /api| BE_SVC

    FE_SVC --> FE1
    FE_SVC --> FE2

    BE_SVC --> BE1
    BE_SVC --> BE2
    BE_SVC --> BE3

    BE1 --> CM
    BE1 --> SEC
    BE2 --> CM
    BE2 --> SEC
    BE3 --> CM
    BE3 --> SEC

    BE1 -->|Connection Pool| DB_MANAGED
    BE2 -->|Connection Pool| DB_MANAGED
    BE3 -->|Connection Pool| DB_MANAGED

    BE1 -.->|Optional| REDIS
    BE2 -.->|Optional| REDIS
    BE3 -.->|Optional| REDIS

    style ING fill:#ff9800
    style FE_SVC fill:#4caf50
    style BE_SVC fill:#4caf50
    style DB_MANAGED fill:#2196f3
    style REDIS fill:#f44336
```

## Key Design Patterns

### 1. **Plugin Architecture**
- Connectors are dynamically registered via decorators
- All connectors inherit from `BaseConnector` abstract class
- Registry pattern for connector discovery and instantiation

### 2. **Multi-Tenancy**
- Path-based tenant isolation (`/api/v1/{tenant_slug}`)
- Foreign key relationships ensure data segregation
- Each tenant has isolated OAuth credentials and connectors

### 3. **Repository Pattern**
- SQLAlchemy ORM abstracts database operations
- Async database access via `asyncpg`
- Connection pooling for performance

### 4. **Factory Pattern**
- `MCPServer` factory creates server instances (now cached via `ServerPool`)
- Connector factory creates connector instances from registry

### 5. **Object Pool Pattern**
- `ServerPool` caches `MCPServer` instances keyed by `tenant_slug:connector_id`
- LRU eviction when pool exceeds `max_size` (default 5,000)
- TTL-based expiry (default 30 minutes) with background reaper (60s interval)

### 6. **Token Bucket Pattern**
- Per-tenant rate limiting with configurable RPM (default 100)
- Refill rate: `rpm / 60` tokens per second; burst capacity equals RPM
- Returns `429 Too Many Requests` with `Retry-After` header

### 7. **Ring Buffer Pattern**
- `EventBuffer` stores last 100 SSE events per session using `OrderedDict`
- FIFO eviction when capacity exceeded
- Supports `Last-Event-ID` header for resumable SSE streams

### 8. **Single-Flight Pattern**
- `SessionManager` ensures only one session is created per concurrent `initialize` request
- Max 10 sessions per tenant+connector key; oldest evicted when limit reached

### 9. **RBAC with Precomputed Permission Sets**
- Roles mapped to frozen permission sets at import time (zero allocation per check)
- API key scopes bridge to roles via `SCOPE_TO_ROLE` for unified permission checks
- `require_permission()` dependency enforced on all admin endpoints
- JWT decode (fast path, ~0.1ms) tried before API key lookup (slow path, bcrypt)

### 10. **Decorator Pattern**
- `@register_connector` decorator for plugin registration
- FastAPI route decorators for API endpoints

### 11. **Adapter Pattern**
- Connectors adapt external APIs to MCP protocol
- `GenericMCPConnector` adapts stdio-based external MCP servers to the same interface
- Each connector translates between MCP tools and provider-specific APIs

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Network Security"
            HTTPS[HTTPS/TLS]
            CORS[CORS Middleware]
        end

        subgraph "Request Validation"
            RATE_LIM["Rate Limiting
Token bucket · per-tenant"]
            ORIGIN_VAL["Origin Validation
MCP_ALLOWED_ORIGINS"]
            CT_VAL["Content-Type Validation
application/json required"]
            SESS_BIND["Session Binding
Mcp-Session-Id"]
        end

        subgraph "Authentication"
            OAUTH[OAuth 2.0 Flow]
            JWT_AUTH["JWT Tokens
30min access · 7d refresh"]
            API_KEY_AUTH["API Keys
3 scopes · bcrypt + LRU cache"]
            STATE["State Token
CSRF Protection"]
        end

        subgraph "Authorization (RBAC)"
            RBAC_PERM["18 Permissions
require_permission() on all endpoints"]
            RBAC_ROLES["4 Roles
platform_admin · tenant_admin
tenant_member · tenant_viewer"]
            TENANT_ISO["Tenant Isolation
Path-based + key scope"]
            TOOL_POL["Global Tool Policies
Block/Warn by glob pattern"]
        end

        subgraph "Audit"
            AUDIT["Audit Log
Fire-and-forget recording
Paginated query endpoints"]
        end

        subgraph "Data Protection"
            TOKEN_ENC["Fernet Encryption
AES-128 · PBKDF2-SHA256"]
            SECRET_MGR["Secret Management
K8s Secrets/Vault"]
            ENV_VAR[Environment Variables]
        end

        subgraph "Input Validation"
            PYDANTIC[Pydantic Models]
            SQL_PREVENT["SQLAlchemy ORM
SQL Injection Prevention"]
        end
    end

    HTTPS --> RATE_LIM
    CORS --> ORIGIN_VAL
    RATE_LIM --> CT_VAL
    ORIGIN_VAL --> CT_VAL
    CT_VAL --> SESS_BIND
    SESS_BIND --> JWT_AUTH
    JWT_AUTH --> API_KEY_AUTH
    API_KEY_AUTH --> RBAC_PERM
    RBAC_PERM --> RBAC_ROLES
    RBAC_ROLES --> TENANT_ISO
    TENANT_ISO --> TOOL_POL
    TOOL_POL --> AUDIT
    OAUTH --> STATE
    STATE --> TOKEN_ENC
    TOKEN_ENC --> SECRET_MGR
    SECRET_MGR --> ENV_VAR
    ENV_VAR --> PYDANTIC
    PYDANTIC --> SQL_PREVENT
```

**Security features** (all feature-flagged under `SAGEMCP_ENABLE_AUTH`):
- **Dual authentication** — JWT decode first (~0.1ms, no DB), API key fallback (bcrypt verify with SHA-256 LRU cache)
- **RBAC** — 4 roles, 18 permissions, `require_permission()` enforced on all 44 admin endpoints
- **Tenant isolation** — Scoped API keys, WebSocket tenant checks, process management guards
- **Global tool policies** — Block/warn on tools by glob pattern; in-memory cache for zero-DB-query enforcement
- **Audit logging** — Fire-and-forget recording of state changes; paginated query endpoints with filtering
- **Field-level encryption** — Fernet AES-128 for tokens, secrets, configs; transparent encrypt/decrypt
- **Rate limiting** — Token-bucket per-tenant RPM with `Retry-After` headers
- **Origin validation** — `MCP_ALLOWED_ORIGINS` restricts which origins can send MCP requests
- **Content-Type enforcement** — Only `application/json` accepted for MCP HTTP POST endpoints
- **Session binding** — `Mcp-Session-Id` binds a client to a specific server instance
- **CORS hardening** — `Mcp-Session-Id` added to `Access-Control-Expose-Headers`

See [Authentication & Authorization](auth.md) for full details, API reference, and examples.

## Performance Considerations

### Server Pool
- **Hit cost**: O(1) dict lookup + LRU touch (~0.01ms)
- **Miss cost**: DB query + connector instantiation (~5-15ms)
- **Eviction**: LRU when pool exceeds 5,000 entries; TTL reaper every 60s
- **Memory**: ~5KB per cached `MCPServer` instance

### Connection Reuse
- **HTTPX**: Async connection pool for external API calls (per-connector)
- **Subprocess persistence**: `MCPProcessManager` keeps external MCP server processes alive with 30s health checks
- **SQLAlchemy**: Async engine with connection pool (default: 5-20 connections)

### Session Management
- **Lookup cost**: O(1) dict access by `session_id`
- **Per-key limit**: Max 10 sessions per `tenant_slug:connector_id` (oldest evicted)
- **TTL**: 30-minute inactivity timeout with 60s background reaper

### Memory Budget (estimated at 3,000 active instances)

| Component | Per-Unit | At Scale | Notes |
|-----------|----------|----------|-------|
| ServerPool entries | ~5KB | ~15MB | 3,000 cached servers |
| SessionManager entries | ~2KB | ~6MB | 3,000 active sessions |
| EventBuffers | ~10KB | ~30MB | 100 events × 100 bytes × 3,000 sessions |
| External processes | ~20MB | ~200MB | Depends on server count |
| **Total (in-process)** | — | **~250MB** | Excluding external runtimes |

## Monitoring & Observability

### Prometheus Metrics

All metrics are prefixed with `sagemcp_` and exposed at `/metrics` (requires `SAGEMCP_ENABLE_METRICS=true`).

**Request Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sagemcp_http_request_duration_seconds` | Histogram | `method`, `path_template`, `status_code` | HTTP request latency |
| `sagemcp_tool_call_duration_seconds` | Histogram | `connector_type`, `tool_name`, `status` | Tool execution latency |
| `sagemcp_tool_calls_total` | Counter | `connector_type`, `status` | Total tool invocations |

**Resource Gauges:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sagemcp_active_sessions` | Gauge | — | Active MCP sessions |
| `sagemcp_pool_size` | Gauge | — | Server pool entries |
| `sagemcp_external_processes` | Gauge | — | Running external MCP processes |
| `sagemcp_memory_usage_bytes` | Gauge | `component` | Memory usage by component |

**Pool Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sagemcp_pool_hits_total` | Counter | — | Server pool cache hits |
| `sagemcp_pool_misses_total` | Counter | — | Server pool cache misses |

> **Cardinality note:** `path_template` uses route templates (e.g., `/api/v1/{tenant_slug}/connectors/{connector_id}/mcp`), not raw paths, to keep cardinality bounded.

### Structured Logging

All log entries are JSON-formatted with the following fields:
- `timestamp`, `level`, `message` — Standard fields
- `tenant_slug`, `connector_id` — Request context
- `request_id` — Correlation ID for distributed tracing
- `duration_ms` — Operation timing

### Health Probes

| Endpoint | K8s Probe Type | Checks |
|----------|---------------|--------|
| `/health/live` | `livenessProbe` | Process is running |
| `/health/ready` | `readinessProbe` | DB reachable, pool initialized |
| `/health/startup` | `startupProbe` | Migrations complete, connectors registered |

```mermaid
graph LR
    subgraph "Application"
        APP["SageMCP Backend
/metrics · /health/*"]
    end

    subgraph "Monitoring Stack"
        PROM["Prometheus
Scrape /metrics"]
        GRAF[Grafana Dashboards]
        ALERT[AlertManager]
    end

    subgraph "Log Aggregation"
        LOGS["Structured JSON Logs
stdout/stderr"]
        ELK["ELK / Loki
Optional"]
    end

    APP -->|metrics| PROM
    APP -->|logs| LOGS
    PROM --> GRAF
    PROM --> ALERT
    LOGS --> ELK
    ELK --> GRAF
```

---

## Summary

SageMCP is a **multi-tenant MCP server platform** that enables Claude Desktop to connect to external services via OAuth-authenticated connectors. The architecture provides:

- **Pooled instances** — `ServerPool` caches up to 5,000 `MCPServer` instances with LRU eviction and 30-min TTL
- **Session management** — `Mcp-Session-Id` tracking with `EventBuffer` ring buffers for resumable SSE streams
- **RBAC & auth** — JWT + API key dual auth, 4 roles with 18 permissions, audit logging, global tool policies ([details](auth.md))
- **Rate limiting** — Per-tenant token-bucket rate limiter (configurable RPM) with `Retry-After` headers
- **Observability** — 11 Prometheus metrics, structured JSON logging, and Kubernetes health probes (`/health/live|ready|startup`)
- **External MCP hosting** — `MCPProcessManager` runs third-party MCP servers as stdio subprocesses with health checks and auto-restart
- **Progressive rollout** — Feature flags (`SAGEMCP_ENABLE_*`) for safe, incremental adoption
- **Protocol compliance** — Supports MCP protocol versions `2025-06-18` and `2024-11-05` with version negotiation

The platform bridges Claude Desktop's MCP protocol with 18 external service APIs (GitHub, GitLab, Bitbucket, Jira, Linear, Confluence, Slack, Discord, Teams, Gmail, Outlook, Google Docs, Google Sheets, Google Slides, Notion, Excel, PowerPoint, Zoom) and any MCP-compatible server through a unified, tenant-aware, production-hardened interface. Shared infrastructure modules (pagination, retry, GraphQL client, structured exceptions) ensure consistent behavior across all connectors.
