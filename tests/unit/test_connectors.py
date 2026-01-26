"""Test connectors module."""

from unittest.mock import Mock, patch

import pytest
from mcp import types

from sage_mcp.connectors.github import GitHubConnector
from sage_mcp.connectors.google_docs import GoogleDocsConnector
from sage_mcp.connectors.jira import JiraConnector
from sage_mcp.connectors.notion import NotionConnector
from sage_mcp.connectors.zoom import ZoomConnector
from sage_mcp.connectors.registry import ConnectorRegistry
from sage_mcp.models.connector import ConnectorType


class TestConnectorRegistry:
    """Test ConnectorRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ConnectorRegistry()
        assert len(registry._connectors) == 0
        assert len(registry._connector_types) == 0

    def test_register_connector(self):
        """Test registering a connector."""
        registry = ConnectorRegistry()

        class TestConnector:
            def __init__(self):
                pass

            @property
            def name(self):
                return "test"

        registry.register(ConnectorType.GITHUB, TestConnector)

        assert len(registry._connectors) == 1
        assert len(registry._connector_types) == 1
        assert ConnectorType.GITHUB in registry._connector_types
        assert "test" in registry._connectors

    def test_get_connector(self):
        """Test getting a connector by type."""
        registry = ConnectorRegistry()

        class TestConnector:
            def __init__(self):
                pass

            @property
            def name(self):
                return "test"

        registry.register(ConnectorType.GITHUB, TestConnector)

        connector = registry.get_connector(ConnectorType.GITHUB)
        assert connector is not None
        assert connector.name == "test"

        # Test non-existent connector
        connector = registry.get_connector(ConnectorType.GITLAB)
        assert connector is None

    def test_get_connector_by_name(self):
        """Test getting a connector by name."""
        registry = ConnectorRegistry()

        class TestConnector:
            def __init__(self):
                pass

            @property
            def name(self):
                return "test"

        registry.register(ConnectorType.GITHUB, TestConnector)

        connector = registry.get_connector_by_name("test")
        assert connector is not None
        assert connector.name == "test"

        # Test non-existent connector
        connector = registry.get_connector_by_name("nonexistent")
        assert connector is None

    def test_list_connectors(self):
        """Test listing all connectors."""
        registry = ConnectorRegistry()

        class TestConnector:
            def __init__(self):
                pass

            @property
            def name(self):
                return "test"

        registry.register(ConnectorType.GITHUB, TestConnector)

        connectors = registry.list_connectors()
        assert len(connectors) == 1
        assert "test" in connectors

    def test_get_connector_info(self):
        """Test getting connector information."""
        registry = ConnectorRegistry()

        class TestConnector:
            def __init__(self):
                pass

            @property
            def name(self):
                return "test"

            @property
            def display_name(self):
                return "Test Connector"

            @property
            def description(self):
                return "A test connector"

            @property
            def requires_oauth(self):
                return True

        registry.register(ConnectorType.GITHUB, TestConnector)

        info = registry.get_connector_info(ConnectorType.GITHUB)
        assert info is not None
        assert info["name"] == "test"
        assert info["display_name"] == "Test Connector"
        assert info["description"] == "A test connector"
        assert info["requires_oauth"] is True
        assert info["type"] == "github"


class TestGitHubConnector:
    """Test GitHubConnector class."""

    def test_github_connector_properties(self):
        """Test GitHub connector properties."""
        connector = GitHubConnector()

        assert connector.display_name == "GitHub"
        assert "GitHub" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting GitHub tools."""
        connector = GitHubConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) > 0

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("github_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "github_list_repositories" in tool_names
        assert "github_get_repository" in tool_names
        assert "github_list_issues" in tool_names
        assert "github_check_token_scopes" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = GitHubConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_oauth(self, sample_connector):
        """Test executing tool with invalid OAuth."""
        connector = GitHubConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_repositories",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.github.GitHubConnector._make_authenticated_request')
    async def test_check_token_scopes(self, mock_request, sample_connector, sample_oauth_credential):
        """Test checking token scopes."""
        connector = GitHubConnector()

        # Mock the GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "login": "testuser",
            "id": 123456,
            "type": "User",
            "name": "Test User",
            "public_repos": 5
        }
        mock_response.headers = {
            "X-OAuth-Scopes": "repo, user:email, read:org",
            "X-Accepted-OAuth-Scopes": ""
        }
        mock_request.return_value = mock_response

        result = await connector._check_token_scopes(sample_oauth_credential)

        assert "testuser" in result
        assert "repo" in result
        assert "user:email" in result
        assert "read:org" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.github.GitHubConnector._make_authenticated_request')
    async def test_list_organizations(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing organizations."""
        connector = GitHubConnector()

        # Mock the GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "login": "testorg",
                "id": 789,
                "description": "Test Organization",
                "url": "https://api.github.com/orgs/testorg",
                "html_url": "https://github.com/testorg"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_organizations(sample_oauth_credential)

        assert "testorg" in result
        assert "total_count" in result
        assert "1" in result  # Should show 1 organization

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = GitHubConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = GitHubConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = GitHubConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False


class TestGoogleDocsConnector:
    """Test GoogleDocsConnector class."""

    def test_google_docs_connector_properties(self):
        """Test Google Docs connector properties."""
        connector = GoogleDocsConnector()

        assert connector.display_name == "Google Docs"
        assert "Google Docs" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Google Docs tools."""
        connector = GoogleDocsConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 10  # We have 10 Google Docs tools

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("google_docs_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "google_docs_list_documents" in tool_names
        assert "google_docs_get_document" in tool_names
        assert "google_docs_read_document_content" in tool_names
        assert "google_docs_search_documents" in tool_names
        assert "google_docs_create_document" in tool_names
        assert "google_docs_append_text" in tool_names
        assert "google_docs_insert_text" in tool_names
        assert "google_docs_export_document" in tool_names
        assert "google_docs_get_permissions" in tool_names
        assert "google_docs_list_shared_documents" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = GoogleDocsConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_oauth(self, sample_connector):
        """Test executing tool with invalid OAuth."""
        connector = GoogleDocsConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_documents",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_docs.GoogleDocsConnector._make_authenticated_request')
    async def test_list_documents(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing documents."""
        connector = GoogleDocsConnector()

        # Mock the Google Drive API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "doc123",
                    "name": "Test Document",
                    "createdTime": "2024-01-01T00:00:00Z",
                    "modifiedTime": "2024-01-02T00:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc123/edit",
                    "owners": [{"displayName": "Test User"}],
                    "starred": False
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_documents({}, sample_oauth_credential)

        assert "Test Document" in result
        assert "doc123" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_docs.GoogleDocsConnector._make_authenticated_request')
    async def test_get_document(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting document metadata."""
        connector = GoogleDocsConnector()

        # Mock both API responses
        doc_response = Mock()
        doc_response.json.return_value = {
            "documentId": "doc123",
            "title": "Test Document",
            "revisionId": "rev123"
        }

        drive_response = Mock()
        drive_response.json.return_value = {
            "id": "doc123",
            "name": "Test Document",
            "createdTime": "2024-01-01T00:00:00Z",
            "modifiedTime": "2024-01-02T00:00:00Z",
            "webViewLink": "https://docs.google.com/document/d/doc123/edit",
            "owners": [{"displayName": "Test User"}],
            "starred": True
        }

        mock_request.side_effect = [doc_response, drive_response]

        result = await connector._get_document({"document_id": "doc123"}, sample_oauth_credential)

        assert "doc123" in result
        assert "Test Document" in result
        assert "rev123" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_docs.GoogleDocsConnector._make_authenticated_request')
    async def test_read_document_content(self, mock_request, sample_connector, sample_oauth_credential):
        """Test reading document content."""
        connector = GoogleDocsConnector()

        # Mock the Docs API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "documentId": "doc123",
            "title": "Test Document",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {
                                    "textRun": {
                                        "content": "Hello, world!\n"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_request.return_value = mock_response

        result = await connector._read_document_content(
            {"document_id": "doc123", "format": "plain_text"},
            sample_oauth_credential
        )

        assert "Test Document" in result
        assert "Hello, world!" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_docs.GoogleDocsConnector._make_authenticated_request')
    async def test_create_document(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a document."""
        connector = GoogleDocsConnector()

        # Mock the create response
        create_response = Mock()
        create_response.json.return_value = {
            "documentId": "new_doc123",
            "title": "New Document"
        }

        # Mock the batch update response (for initial content)
        update_response = Mock()
        update_response.json.return_value = {}

        mock_request.side_effect = [create_response, update_response]

        result = await connector._create_document(
            {"title": "New Document", "initial_content": "Initial text"},
            sample_oauth_credential
        )

        assert "new_doc123" in result
        assert "New Document" in result
        assert "web_view_link" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_docs.GoogleDocsConnector._make_authenticated_request')
    async def test_search_documents(self, mock_request, sample_connector, sample_oauth_credential):
        """Test searching documents."""
        connector = GoogleDocsConnector()

        # Mock the search response
        mock_response = Mock()
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "doc456",
                    "name": "Search Result",
                    "modifiedTime": "2024-01-03T00:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc456/edit"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._search_documents(
            {"query": "test", "page_size": 20},
            sample_oauth_credential
        )

        assert "Search Result" in result
        assert "doc456" in result
        assert "count" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = GoogleDocsConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = GoogleDocsConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = GoogleDocsConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False

    def test_extract_plain_text(self):
        """Test extracting plain text from document structure."""
        connector = GoogleDocsConnector()

        doc_data = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "First line\n"}},
                                {"textRun": {"content": "Second line\n"}}
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Third line\n"}}
                            ]
                        }
                    }
                ]
            }
        }

        text = connector._extract_plain_text(doc_data)
        assert "First line" in text
        assert "Second line" in text
        assert "Third line" in text


class TestJiraConnector:
    """Test JiraConnector class."""

    def test_jira_connector_properties(self):
        """Test Jira connector properties."""
        connector = JiraConnector()

        assert connector.display_name == "Jira"
        assert "Jira" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Jira tools."""
        connector = JiraConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 20  # Jira has 20 tools

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("jira_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "jira_search_issues" in tool_names
        assert "jira_get_issue" in tool_names
        assert "jira_create_issue" in tool_names
        assert "jira_update_issue" in tool_names
        assert "jira_list_projects" in tool_names
        assert "jira_list_boards" in tool_names
        assert "jira_list_sprints" in tool_names
        assert "jira_search_users" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = JiraConnector()

        # Mock _get_cloud_id
        with patch.object(connector, '_get_cloud_id', return_value='test-cloud-id'):
            result = await connector.execute_tool(
                sample_connector,
                "unknown_tool",
                {},
                sample_oauth_credential
            )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_oauth(self, sample_connector):
        """Test executing tool with invalid OAuth."""
        connector = JiraConnector()

        result = await connector.execute_tool(
            sample_connector,
            "search_issues",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_get_cloud_id(self, mock_request, sample_oauth_credential):
        """Test getting Jira cloud ID."""
        connector = JiraConnector()

        # Mock the Jira accessible resources response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "test-cloud-id-123",
                "name": "Test Jira Site",
                "url": "https://test.atlassian.net"
            }
        ]
        mock_request.return_value = mock_response

        cloud_id = await connector._get_cloud_id(sample_oauth_credential)

        assert cloud_id == "test-cloud-id-123"
        assert mock_request.called
        # Verify caching works
        cloud_id2 = await connector._get_cloud_id(sample_oauth_credential)
        assert cloud_id2 == "test-cloud-id-123"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_search_issues(self, mock_request, sample_oauth_credential):
        """Test searching Jira issues."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "total": 2,
            "issues": [
                {
                    "key": "PROJ-123",
                    "fields": {
                        "summary": "Test issue 1",
                        "status": {"name": "Open"}
                    }
                },
                {
                    "key": "PROJ-124",
                    "fields": {
                        "summary": "Test issue 2",
                        "status": {"name": "In Progress"}
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._search_issues(
            "test-cloud-id",
            {"jql": "project = PROJ"},
            sample_oauth_credential
        )

        assert "PROJ-123" in result
        assert "PROJ-124" in result
        assert "Test issue 1" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_create_issue(self, mock_request, sample_oauth_credential):
        """Test creating a Jira issue."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "PROJ-125",
            "id": "10001",
            "self": "https://test.atlassian.net/rest/api/3/issue/10001"
        }
        mock_request.return_value = mock_response

        result = await connector._create_issue(
            "test-cloud-id",
            {
                "project_key": "PROJ",
                "summary": "New test issue",
                "issue_type": "Bug",
                "description": "This is a test issue"
            },
            sample_oauth_credential
        )

        assert "PROJ-125" in result
        assert mock_request.called

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_get_transitions(self, mock_request, sample_oauth_credential):
        """Test getting issue transitions."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "transitions": [
                {
                    "id": "11",
                    "name": "In Progress",
                    "to": {"name": "In Progress"}
                },
                {
                    "id": "21",
                    "name": "Done",
                    "to": {"name": "Done"}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._get_transitions(
            "test-cloud-id",
            {"issue_key": "PROJ-123"},
            sample_oauth_credential
        )

        assert "In Progress" in result
        assert "Done" in result
        assert '"id": "11"' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_list_projects(self, mock_request, sample_oauth_credential):
        """Test listing Jira projects."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "10000",
                "key": "PROJ",
                "name": "Test Project",
                "projectTypeKey": "software",
                "lead": {"displayName": "Test User"}
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_projects(
            "test-cloud-id",
            {},
            sample_oauth_credential
        )

        assert "PROJ" in result
        assert "Test Project" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_list_boards(self, mock_request, sample_oauth_credential):
        """Test listing Jira boards."""
        connector = JiraConnector()

        # Mock the Jira Agile API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "id": 1,
                    "name": "Test Board",
                    "type": "scrum",
                    "location": {"projectKey": "PROJ"}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_boards(
            "test-cloud-id",
            {},
            sample_oauth_credential
        )

        assert "Test Board" in result
        assert "scrum" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_list_sprints(self, mock_request, sample_oauth_credential):
        """Test listing sprints."""
        connector = JiraConnector()

        # Mock the Jira Agile API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "id": 1,
                    "name": "Sprint 1",
                    "state": "active",
                    "startDate": "2024-01-01T00:00:00.000Z",
                    "endDate": "2024-01-14T00:00:00.000Z"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_sprints(
            "test-cloud-id",
            {"board_id": 1},
            sample_oauth_credential
        )

        assert "Sprint 1" in result
        assert "active" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_search_users(self, mock_request, sample_oauth_credential):
        """Test searching users."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "accountId": "557058:12345",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
                "active": True
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._search_users(
            "test-cloud-id",
            {"query": "test"},
            sample_oauth_credential
        )

        assert "Test User" in result
        assert "557058:12345" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.jira.JiraConnector._make_authenticated_request')
    async def test_add_comment(self, mock_request, sample_oauth_credential):
        """Test adding a comment."""
        connector = JiraConnector()

        # Mock the Jira API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "10001",
            "created": "2024-01-01T00:00:00.000Z",
            "author": {"displayName": "Test User"}
        }
        mock_request.return_value = mock_response

        result = await connector._add_comment(
            "test-cloud-id",
            {"issue_key": "PROJ-123", "body": "Test comment"},
            sample_oauth_credential
        )

        assert "10001" in result

    @pytest.mark.asyncio
    async def test_read_resource_project(self, sample_connector, sample_oauth_credential):
        """Test reading a project resource."""
        connector = JiraConnector()

        with patch.object(connector, '_get_cloud_id', return_value='test-cloud-id'):
            with patch.object(connector, '_make_authenticated_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "key": "PROJ",
                    "name": "Test Project"
                }
                mock_request.return_value = mock_response

                result = await connector.read_resource(
                    sample_connector,
                    "project/PROJ",
                    sample_oauth_credential
                )

                assert "PROJ" in result
                assert "Test Project" in result

    @pytest.mark.asyncio
    async def test_read_resource_issue(self, sample_connector, sample_oauth_credential):
        """Test reading an issue resource."""
        connector = JiraConnector()

        with patch.object(connector, '_get_cloud_id', return_value='test-cloud-id'):
            with patch.object(connector, '_make_authenticated_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "key": "PROJ-123",
                    "fields": {"summary": "Test issue"}
                }
                mock_request.return_value = mock_response

                result = await connector.read_resource(
                    sample_connector,
                    "issue/PROJ-123",
                    sample_oauth_credential
                )

                assert "PROJ-123" in result

    @pytest.mark.asyncio
    async def test_read_resource_invalid(self, sample_connector, sample_oauth_credential):
        """Test reading an invalid resource."""
        connector = JiraConnector()

        with patch.object(connector, '_get_cloud_id', return_value='test-cloud-id'):
            result = await connector.read_resource(
                sample_connector,
                "invalid",
                sample_oauth_credential
            )

            assert "Error" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = JiraConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = JiraConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = JiraConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False

    def test_get_api_base_url(self):
        """Test constructing API base URL."""
        connector = JiraConnector()

        url = connector._get_api_base_url("test-cloud-id")
        assert url == "https://api.atlassian.com/ex/jira/test-cloud-id/rest/api/3"


class TestNotionConnector:
    """Test NotionConnector class."""

    def test_notion_connector_properties(self):
        """Test Notion connector properties."""
        connector = NotionConnector()

        assert connector.display_name == "Notion"
        assert "Notion" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Notion tools."""
        connector = NotionConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 10  # We have 10 Notion tools

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("notion_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "notion_list_databases" in tool_names
        assert "notion_search" in tool_names
        assert "notion_get_page" in tool_names
        assert "notion_get_page_content" in tool_names
        assert "notion_get_database" in tool_names
        assert "notion_query_database" in tool_names
        assert "notion_create_page" in tool_names
        assert "notion_append_block_children" in tool_names
        assert "notion_update_page" in tool_names
        assert "notion_get_block" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = NotionConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_oauth(self, sample_connector):
        """Test executing tool with invalid OAuth."""
        connector = NotionConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_databases",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_list_databases(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing databases."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "db123",
                    "object": "database",
                    "title": [{"plain_text": "Test Database"}],
                    "created_time": "2024-01-01T00:00:00Z",
                    "last_edited_time": "2024-01-02T00:00:00Z",
                    "url": "https://notion.so/db123"
                }
            ],
            "has_more": False
        }
        mock_request.return_value = mock_response

        result = await connector._list_databases({}, sample_oauth_credential)

        assert "Test Database" in result
        assert "db123" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_search(self, mock_request, sample_connector, sample_oauth_credential):
        """Test searching pages and databases."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page123",
                    "object": "page",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [{"plain_text": "Test Page"}]
                        }
                    },
                    "created_time": "2024-01-01T00:00:00Z",
                    "last_edited_time": "2024-01-02T00:00:00Z",
                    "url": "https://notion.so/page123"
                }
            ],
            "has_more": False
        }
        mock_request.return_value = mock_response

        result = await connector._search(
            {"query": "test", "page_size": 20},
            sample_oauth_credential
        )

        assert "Test Page" in result
        assert "page123" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_get_page(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a page by ID."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "page123",
            "created_time": "2024-01-01T00:00:00Z",
            "last_edited_time": "2024-01-02T00:00:00Z",
            "archived": False,
            "url": "https://notion.so/page123",
            "properties": {}
        }
        mock_request.return_value = mock_response

        result = await connector._get_page({"page_id": "page123"}, sample_oauth_credential)

        assert "page123" in result
        assert "archived" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_get_page_content(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting page content."""
        connector = NotionConnector()

        # Mock the page response
        page_response = Mock()
        page_response.json.return_value = {
            "id": "page123",
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Test Page"}]
                }
            }
        }

        # Mock the blocks response
        blocks_response = Mock()
        blocks_response.json.return_value = {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "plain_text": "Hello, world!"}
                        ]
                    }
                }
            ]
        }

        mock_request.side_effect = [page_response, blocks_response]

        result = await connector._get_page_content(
            {"page_id": "page123", "format": "plain_text"},
            sample_oauth_credential
        )

        assert "Test Page" in result
        assert "Hello, world!" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_create_page(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a page."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "new_page123",
            "url": "https://notion.so/new_page123",
            "created_time": "2024-01-01T00:00:00Z"
        }
        mock_request.return_value = mock_response

        result = await connector._create_page(
            {
                "parent_id": "db123",
                "title": "New Page",
                "content": "Initial content"
            },
            sample_oauth_credential
        )

        assert "new_page123" in result
        assert "url" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_query_database(self, mock_request, sample_connector, sample_oauth_credential):
        """Test querying a database."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page456",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [{"plain_text": "Database Entry"}]
                        }
                    },
                    "created_time": "2024-01-01T00:00:00Z",
                    "last_edited_time": "2024-01-02T00:00:00Z",
                    "url": "https://notion.so/page456"
                }
            ],
            "has_more": False
        }
        mock_request.return_value = mock_response

        result = await connector._query_database(
            {"database_id": "db123"},
            sample_oauth_credential
        )

        assert "Database Entry" in result
        assert "page456" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.notion.NotionConnector._make_authenticated_request')
    async def test_append_block_children(self, mock_request, sample_connector, sample_oauth_credential):
        """Test appending block children."""
        connector = NotionConnector()

        # Mock the Notion API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"id": "block123"}]
        }
        mock_request.return_value = mock_response

        result = await connector._append_block_children(
            {"page_id": "page123", "content": "New content"},
            sample_oauth_credential
        )

        assert "success" in result
        assert "blocks_added" in result

    @pytest.mark.asyncio
    async def test_read_resource_page(self, sample_connector, sample_oauth_credential):
        """Test reading a page resource."""
        connector = NotionConnector()

        with patch.object(connector, '_make_authenticated_request') as mock_request:
            page_response = Mock()
            page_response.json.return_value = {
                "id": "page123",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Test Page"}]
                    }
                }
            }

            blocks_response = Mock()
            blocks_response.json.return_value = {
                "results": []
            }

            mock_request.side_effect = [page_response, blocks_response]

            result = await connector.read_resource(
                sample_connector,
                "page/page123",
                sample_oauth_credential
            )

            assert "Test Page" in result

    @pytest.mark.asyncio
    async def test_read_resource_database(self, sample_connector, sample_oauth_credential):
        """Test reading a database resource."""
        connector = NotionConnector()

        with patch.object(connector, '_make_authenticated_request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "db123",
                "title": [{"plain_text": "Test Database"}],
                "properties": {
                    "Name": {"type": "title"},
                    "Status": {"type": "select"}
                }
            }
            mock_request.return_value = mock_response

            result = await connector.read_resource(
                sample_connector,
                "database/db123",
                sample_oauth_credential
            )

            assert "Test Database" in result
            assert "Properties" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = NotionConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = NotionConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = NotionConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False

    def test_extract_page_title(self):
        """Test extracting page title from page data."""
        connector = NotionConnector()

        page_data = {
            "properties": {
                "Title": {
                    "type": "title",
                    "title": [{"plain_text": "My Page Title"}]
                }
            }
        }

        title = connector._extract_page_title(page_data)
        assert title == "My Page Title"

    def test_extract_plain_text_from_blocks(self):
        """Test extracting plain text from Notion blocks."""
        connector = NotionConnector()

        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "plain_text": "First paragraph"}
                    ]
                }
            },
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {"type": "text", "plain_text": "Heading"}
                    ]
                }
            },
            {
                "type": "code",
                "code": {
                    "rich_text": [
                        {"type": "text", "plain_text": "console.log('test')"}
                    ]
                }
            }
        ]

        text = connector._extract_plain_text_from_blocks(blocks)
        assert "First paragraph" in text
        assert "Heading" in text
        assert "console.log('test')" in text


class TestZoomConnector:
    """Test ZoomConnector class."""

    def test_zoom_connector_properties(self):
        """Test Zoom connector properties."""
        connector = ZoomConnector()

        assert connector.display_name == "Zoom"
        assert "Zoom" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Zoom tools."""
        connector = ZoomConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 12  # We have 12 Zoom tools

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("zoom_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "zoom_list_meetings" in tool_names
        assert "zoom_get_meeting" in tool_names
        assert "zoom_create_meeting" in tool_names
        assert "zoom_update_meeting" in tool_names
        assert "zoom_delete_meeting" in tool_names
        assert "zoom_get_user" in tool_names
        assert "zoom_list_recordings" in tool_names
        assert "zoom_get_meeting_recordings" in tool_names
        assert "zoom_list_webinars" in tool_names
        assert "zoom_get_webinar" in tool_names
        assert "zoom_list_meeting_participants" in tool_names
        assert "zoom_get_meeting_invitation" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = ZoomConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_oauth(self, sample_connector):
        """Test executing tool with invalid OAuth."""
        connector = ZoomConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_meetings",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_list_meetings(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing meetings."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "meetings": [
                {
                    "id": "12345678",
                    "topic": "Test Meeting",
                    "type": 2,
                    "start_time": "2024-01-15T10:00:00Z",
                    "duration": 60,
                    "timezone": "America/New_York",
                    "join_url": "https://zoom.us/j/12345678",
                    "agenda": "Discuss project updates"
                }
            ],
            "total_records": 1
        }
        mock_request.return_value = mock_response

        result = await connector._list_meetings({}, sample_oauth_credential)

        assert "Test Meeting" in result
        assert "12345678" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_get_meeting(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a meeting by ID."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "12345678",
            "uuid": "abc-123-def-456",
            "host_id": "host123",
            "topic": "Test Meeting",
            "type": 2,
            "status": "waiting",
            "start_time": "2024-01-15T10:00:00Z",
            "duration": 60,
            "timezone": "America/New_York",
            "agenda": "Test agenda",
            "created_at": "2024-01-10T12:00:00Z",
            "join_url": "https://zoom.us/j/12345678",
            "password": "abc123",
            "settings": {}
        }
        mock_request.return_value = mock_response

        result = await connector._get_meeting({"meeting_id": "12345678"}, sample_oauth_credential)

        assert "12345678" in result
        assert "Test Meeting" in result
        assert "join_url" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_create_meeting(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a meeting."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "87654321",
            "uuid": "new-uuid-123",
            "host_id": "host123",
            "topic": "New Test Meeting",
            "type": 2,
            "start_time": "2024-01-20T14:00:00Z",
            "duration": 90,
            "timezone": "UTC",
            "join_url": "https://zoom.us/j/87654321",
            "password": "xyz789",
            "created_at": "2024-01-15T10:00:00Z"
        }
        mock_request.return_value = mock_response

        result = await connector._create_meeting(
            {
                "topic": "New Test Meeting",
                "type": 2,
                "start_time": "2024-01-20T14:00:00Z",
                "duration": 90
            },
            sample_oauth_credential
        )

        assert "87654321" in result
        assert "New Test Meeting" in result
        assert "join_url" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_update_meeting(self, mock_request, sample_connector, sample_oauth_credential):
        """Test updating a meeting."""
        connector = ZoomConnector()

        # Mock the Zoom API response (PATCH returns no content)
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        result = await connector._update_meeting(
            {
                "meeting_id": "12345678",
                "topic": "Updated Meeting Title"
            },
            sample_oauth_credential
        )

        assert "success" in result
        assert "12345678" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_delete_meeting(self, mock_request, sample_connector, sample_oauth_credential):
        """Test deleting a meeting."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_request.return_value = mock_response

        result = await connector._delete_meeting(
            {"meeting_id": "12345678"},
            sample_oauth_credential
        )

        assert "success" in result
        assert "deleted" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_get_user(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting user information."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "user123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "type": 2,
            "pmi": 1234567890,
            "timezone": "America/New_York",
            "verified": 1,
            "created_at": "2020-01-01T00:00:00Z",
            "last_login_time": "2024-01-15T08:00:00Z",
            "pic_url": "https://example.com/pic.jpg",
            "account_id": "account123"
        }
        mock_request.return_value = mock_response

        result = await connector._get_user({"user_id": "me"}, sample_oauth_credential)

        assert "john.doe@example.com" in result
        assert "John" in result
        assert "user123" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_list_recordings(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing cloud recordings."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "meetings": [
                {
                    "id": "rec123",
                    "uuid": "rec-uuid-123",
                    "topic": "Recorded Meeting",
                    "start_time": "2024-01-10T10:00:00Z",
                    "duration": 60,
                    "total_size": 1024000,
                    "recording_count": 2,
                    "recording_files": [
                        {
                            "id": "file1",
                            "file_type": "MP4",
                            "file_size": 512000,
                            "download_url": "https://zoom.us/rec/download/file1",
                            "play_url": "https://zoom.us/rec/play/file1"
                        }
                    ]
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_recordings({}, sample_oauth_credential)

        assert "Recorded Meeting" in result
        assert "rec123" in result
        assert "recording_files" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_get_meeting_recordings(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting recordings for a specific meeting."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "uuid": "meeting-uuid",
            "id": "meeting123",
            "account_id": "account123",
            "host_id": "host123",
            "topic": "Test Meeting",
            "start_time": "2024-01-10T10:00:00Z",
            "duration": 60,
            "total_size": 2048000,
            "recording_count": 3,
            "recording_files": [
                {
                    "id": "file1",
                    "meeting_id": "meeting123",
                    "recording_start": "2024-01-10T10:00:00Z",
                    "recording_end": "2024-01-10T11:00:00Z",
                    "file_type": "MP4",
                    "file_size": 1024000,
                    "download_url": "https://zoom.us/rec/download/file1",
                    "play_url": "https://zoom.us/rec/play/file1",
                    "status": "completed"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._get_meeting_recordings(
            {"meeting_id": "meeting123"},
            sample_oauth_credential
        )

        assert "meeting123" in result
        assert "Test Meeting" in result
        assert "recording_files" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_list_webinars(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing webinars."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "webinars": [
                {
                    "id": "web123",
                    "uuid": "web-uuid-123",
                    "topic": "Test Webinar",
                    "type": 5,
                    "start_time": "2024-01-20T15:00:00Z",
                    "duration": 120,
                    "timezone": "UTC",
                    "join_url": "https://zoom.us/w/web123",
                    "agenda": "Webinar agenda"
                }
            ],
            "total_records": 1
        }
        mock_request.return_value = mock_response

        result = await connector._list_webinars({}, sample_oauth_credential)

        assert "Test Webinar" in result
        assert "web123" in result
        assert "webinars" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_list_meeting_participants(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing meeting participants."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "participants": [
                {
                    "id": "part1",
                    "user_id": "user123",
                    "name": "John Doe",
                    "user_email": "john@example.com",
                    "join_time": "2024-01-10T10:00:00Z",
                    "leave_time": "2024-01-10T11:00:00Z",
                    "duration": 60,
                    "status": "in_meeting"
                }
            ],
            "total_records": 1
        }
        mock_request.return_value = mock_response

        result = await connector._list_meeting_participants(
            {"meeting_id": "meeting123"},
            sample_oauth_credential
        )

        assert "John Doe" in result
        assert "john@example.com" in result
        assert "participants" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.zoom.ZoomConnector._make_authenticated_request')
    async def test_get_meeting_invitation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting meeting invitation."""
        connector = ZoomConnector()

        # Mock the Zoom API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "invitation": "You are invited to join:\nTest Meeting\nTime: Jan 15, 2024 10:00 AM\nJoin URL: https://zoom.us/j/12345678"
        }
        mock_request.return_value = mock_response

        result = await connector._get_meeting_invitation(
            {"meeting_id": "12345678"},
            sample_oauth_credential
        )

        assert "invitation" in result
        assert "Test Meeting" in result

    @pytest.mark.asyncio
    async def test_read_resource_meeting(self, sample_connector, sample_oauth_credential):
        """Test reading a meeting resource."""
        connector = ZoomConnector()

        with patch.object(connector, '_make_authenticated_request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "12345678",
                "topic": "Test Meeting",
                "start_time": "2024-01-15T10:00:00Z",
                "duration": 60,
                "join_url": "https://zoom.us/j/12345678",
                "agenda": "Test agenda"
            }
            mock_request.return_value = mock_response

            result = await connector.read_resource(
                sample_connector,
                "meeting/12345678",
                sample_oauth_credential
            )

            assert "Test Meeting" in result
            assert "12345678" in result
            assert "Join URL" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = ZoomConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = ZoomConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = ZoomConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False
