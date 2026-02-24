"""Test connectors module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp import types

from sage_mcp.connectors.github import GitHubConnector
from sage_mcp.connectors.gmail import GmailConnector
from sage_mcp.connectors.google_docs import GoogleDocsConnector
from sage_mcp.connectors.google_sheets import GoogleSheetsConnector
from sage_mcp.connectors.google_slides import GoogleSlidesConnector
from sage_mcp.connectors.jira import JiraConnector
from sage_mcp.connectors.notion import NotionConnector
from sage_mcp.connectors.zoom import ZoomConnector
from sage_mcp.connectors.outlook import OutlookConnector
from sage_mcp.connectors.teams import TeamsConnector
from sage_mcp.connectors.excel import ExcelConnector
from sage_mcp.connectors.powerpoint import PowerPointConnector
from sage_mcp.connectors.confluence import ConfluenceConnector
from sage_mcp.connectors.gitlab import GitLabConnector
from sage_mcp.connectors.bitbucket import BitbucketConnector
from sage_mcp.connectors.linear import LinearConnector
from sage_mcp.connectors.discord import DiscordConnector
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


class TestGoogleSheetsConnector:
    """Test GoogleSheetsConnector class."""

    def test_google_sheets_connector_properties(self):
        """Test Google Sheets connector properties."""
        connector = GoogleSheetsConnector()

        assert connector.display_name == "Google Sheets"
        assert "Google Sheets" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Google Sheets tools."""
        connector = GoogleSheetsConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 14

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("google_sheets_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "google_sheets_list_spreadsheets" in tool_names
        assert "google_sheets_get_spreadsheet" in tool_names
        assert "google_sheets_read_range" in tool_names
        assert "google_sheets_write_range" in tool_names
        assert "google_sheets_append_rows" in tool_names
        assert "google_sheets_clear_range" in tool_names
        assert "google_sheets_create_spreadsheet" in tool_names
        assert "google_sheets_add_sheet" in tool_names
        assert "google_sheets_delete_sheet" in tool_names
        assert "google_sheets_get_sheet_metadata" in tool_names
        assert "google_sheets_batch_update" in tool_names
        assert "google_sheets_find_and_replace" in tool_names
        assert "google_sheets_format_range" in tool_names
        assert "google_sheets_search_spreadsheets" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = GoogleSheetsConnector()

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
        connector = GoogleSheetsConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_spreadsheets",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_list_spreadsheets(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing spreadsheets."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "sheet123",
                    "name": "Budget 2024",
                    "createdTime": "2024-01-01T00:00:00Z",
                    "modifiedTime": "2024-01-15T00:00:00Z",
                    "webViewLink": "https://docs.google.com/spreadsheets/d/sheet123/edit",
                    "owners": [{"displayName": "Test User"}],
                    "starred": False
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_spreadsheets({}, sample_oauth_credential)

        assert "Budget 2024" in result
        assert "sheet123" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_get_spreadsheet(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting spreadsheet metadata."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "spreadsheetId": "sheet123",
            "properties": {
                "title": "Budget 2024",
                "locale": "en_US",
                "timeZone": "America/New_York"
            },
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123/edit",
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1",
                        "index": 0,
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 26,
                            "frozenRowCount": 1,
                            "frozenColumnCount": 0
                        }
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._get_spreadsheet(
            {"spreadsheet_id": "sheet123"},
            sample_oauth_credential
        )

        assert "sheet123" in result
        assert "Budget 2024" in result
        assert "Sheet1" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_read_range(self, mock_request, sample_connector, sample_oauth_credential):
        """Test reading a cell range."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "range": "Sheet1!A1:C3",
            "majorDimension": "ROWS",
            "values": [
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "London"]
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._read_range(
            {"spreadsheet_id": "sheet123", "range": "Sheet1!A1:C3"},
            sample_oauth_credential
        )

        assert "Sheet1!A1:C3" in result
        assert "Alice" in result
        assert "Bob" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_write_range(self, mock_request, sample_connector, sample_oauth_credential):
        """Test writing to a cell range."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        mock_request.return_value = mock_response

        result = await connector._write_range(
            {
                "spreadsheet_id": "sheet123",
                "range": "Sheet1!A1:B2",
                "values": [["Name", "Age"], ["Alice", 30]]
            },
            sample_oauth_credential
        )

        assert "updated_range" in result
        assert "updated_cells" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_create_spreadsheet(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a spreadsheet."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "spreadsheetId": "new_sheet456",
            "properties": {"title": "New Spreadsheet"},
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/new_sheet456/edit",
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._create_spreadsheet(
            {"title": "New Spreadsheet"},
            sample_oauth_credential
        )

        assert "new_sheet456" in result
        assert "New Spreadsheet" in result
        assert "url" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_sheets.GoogleSheetsConnector._make_authenticated_request')
    async def test_search_spreadsheets(self, mock_request, sample_connector, sample_oauth_credential):
        """Test searching spreadsheets."""
        connector = GoogleSheetsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "sheet789",
                    "name": "Q4 Report",
                    "modifiedTime": "2024-02-01T00:00:00Z",
                    "webViewLink": "https://docs.google.com/spreadsheets/d/sheet789/edit"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._search_spreadsheets(
            {"query": "Q4", "page_size": 20},
            sample_oauth_credential
        )

        assert "Q4 Report" in result
        assert "sheet789" in result
        assert "count" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = GoogleSheetsConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = GoogleSheetsConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = GoogleSheetsConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False


class TestGmailConnector:
    """Test GmailConnector class."""

    def test_gmail_connector_properties(self):
        """Test Gmail connector properties."""
        connector = GmailConnector()

        assert connector.display_name == "Gmail"
        assert "Gmail" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Gmail tools."""
        connector = GmailConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 15

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("gmail_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "gmail_list_messages" in tool_names
        assert "gmail_get_message" in tool_names
        assert "gmail_search_messages" in tool_names
        assert "gmail_send_message" in tool_names
        assert "gmail_reply_to_message" in tool_names
        assert "gmail_forward_message" in tool_names
        assert "gmail_list_threads" in tool_names
        assert "gmail_get_thread" in tool_names
        assert "gmail_list_labels" in tool_names
        assert "gmail_create_label" in tool_names
        assert "gmail_modify_labels" in tool_names
        assert "gmail_trash_message" in tool_names
        assert "gmail_untrash_message" in tool_names
        assert "gmail_create_draft" in tool_names
        assert "gmail_list_drafts" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = GmailConnector()

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
        connector = GmailConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_messages",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_list_messages(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing messages."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [
                {"id": "msg001", "threadId": "thread001"},
                {"id": "msg002", "threadId": "thread002"}
            ],
            "resultSizeEstimate": 2
        }
        mock_request.return_value = mock_response

        result = await connector._list_messages({}, sample_oauth_credential)

        assert "msg001" in result
        assert "msg002" in result
        assert "resultSizeEstimate" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_get_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a specific message."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Hello, this is a test",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 +0000"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0IG1lc3NhZ2Uu"
                }
            }
        }
        mock_request.return_value = mock_response

        result = await connector._get_message({"id": "msg001"}, sample_oauth_credential)

        assert "msg001" in result
        assert "Test Email" in result
        assert "sender@example.com" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_send_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test sending a message."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg_sent_001",
            "threadId": "thread_new_001",
            "labelIds": ["SENT"]
        }
        mock_request.return_value = mock_response

        result = await connector._send_message(
            {
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "body": "Test body content"
            },
            sample_oauth_credential
        )

        assert "msg_sent_001" in result
        assert "thread_new_001" in result
        assert mock_request.called

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_list_threads(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing threads."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "threads": [
                {"id": "thread001", "snippet": "First thread", "historyId": "12345"},
                {"id": "thread002", "snippet": "Second thread", "historyId": "12346"}
            ],
            "resultSizeEstimate": 2
        }
        mock_request.return_value = mock_response

        result = await connector._list_threads({}, sample_oauth_credential)

        assert "thread001" in result
        assert "thread002" in result
        assert "resultSizeEstimate" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_list_labels(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing labels."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "SENT", "name": "SENT", "type": "system"},
                {"id": "Label_1", "name": "Work", "type": "user"}
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_labels(sample_oauth_credential)

        assert "INBOX" in result
        assert "SENT" in result
        assert "Work" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_search_messages(self, mock_request, sample_connector, sample_oauth_credential):
        """Test searching messages."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [
                {"id": "msg_search_001", "threadId": "thread_s001"}
            ],
            "resultSizeEstimate": 1
        }
        mock_request.return_value = mock_response

        result = await connector._search_messages(
            {"query": "from:boss@company.com"},
            sample_oauth_credential
        )

        assert "msg_search_001" in result
        assert "resultSizeEstimate" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gmail.GmailConnector._make_authenticated_request')
    async def test_trash_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test trashing a message."""
        connector = GmailConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg_trash_001",
            "threadId": "thread_t001",
            "labelIds": ["TRASH"]
        }
        mock_request.return_value = mock_response

        result = await connector._trash_message(
            {"id": "msg_trash_001"},
            sample_oauth_credential
        )

        assert "msg_trash_001" in result
        assert "TRASH" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = GmailConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = GmailConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = GmailConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False


class TestGoogleSlidesConnector:
    """Test GoogleSlidesConnector class."""

    def test_google_slides_connector_properties(self):
        """Test Google Slides connector properties."""
        connector = GoogleSlidesConnector()

        assert connector.display_name == "Google Slides"
        assert "Google Slides" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools(self, sample_connector, sample_oauth_credential):
        """Test getting Google Slides tools."""
        connector = GoogleSlidesConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 11

        # Check that all tools have the correct naming convention
        for tool in tools:
            assert tool.name.startswith("google_slides_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        # Check for specific tools
        tool_names = [tool.name for tool in tools]
        assert "google_slides_list_presentations" in tool_names
        assert "google_slides_get_presentation" in tool_names
        assert "google_slides_get_slide" in tool_names
        assert "google_slides_create_presentation" in tool_names
        assert "google_slides_add_slide" in tool_names
        assert "google_slides_delete_slide" in tool_names
        assert "google_slides_add_text" in tool_names
        assert "google_slides_replace_text" in tool_names
        assert "google_slides_get_speaker_notes" in tool_names
        assert "google_slides_update_speaker_notes" in tool_names
        assert "google_slides_duplicate_slide" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool."""
        connector = GoogleSlidesConnector()

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
        connector = GoogleSlidesConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_presentations",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_slides.GoogleSlidesConnector._make_authenticated_request')
    async def test_list_presentations(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing presentations."""
        connector = GoogleSlidesConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "pres123",
                    "name": "Q4 Review Deck",
                    "createdTime": "2024-01-01T00:00:00Z",
                    "modifiedTime": "2024-01-20T00:00:00Z",
                    "webViewLink": "https://docs.google.com/presentation/d/pres123/edit",
                    "owners": [{"displayName": "Test User"}],
                    "starred": False
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_presentations({}, sample_oauth_credential)

        assert "Q4 Review Deck" in result
        assert "pres123" in result
        assert "count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_slides.GoogleSlidesConnector._make_authenticated_request')
    async def test_get_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting presentation metadata."""
        connector = GoogleSlidesConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "presentationId": "pres123",
            "title": "Q4 Review Deck",
            "locale": "en",
            "slides": [
                {
                    "objectId": "slide001",
                    "slideProperties": {"layoutObjectId": "layout_TITLE"},
                    "pageElements": [{"objectId": "elem1"}, {"objectId": "elem2"}]
                },
                {
                    "objectId": "slide002",
                    "slideProperties": {"layoutObjectId": "layout_BLANK"},
                    "pageElements": []
                }
            ],
            "pageSize": {"width": {"magnitude": 9144000, "unit": "EMU"}, "height": {"magnitude": 6858000, "unit": "EMU"}},
            "revisionId": "rev_abc"
        }
        mock_request.return_value = mock_response

        result = await connector._get_presentation(
            {"presentation_id": "pres123"},
            sample_oauth_credential
        )

        assert "pres123" in result
        assert "Q4 Review Deck" in result
        assert "slide001" in result
        assert "slide_count" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_slides.GoogleSlidesConnector._make_authenticated_request')
    async def test_create_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a presentation."""
        connector = GoogleSlidesConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "presentationId": "new_pres456",
            "title": "New Deck",
            "slides": [
                {"objectId": "slide_default"}
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._create_presentation(
            {"title": "New Deck"},
            sample_oauth_credential
        )

        assert "new_pres456" in result
        assert "New Deck" in result
        assert "web_view_link" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.google_slides.GoogleSlidesConnector._make_authenticated_request')
    async def test_get_slide(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a specific slide by index."""
        connector = GoogleSlidesConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "presentationId": "pres123",
            "slides": [
                {
                    "objectId": "slide001",
                    "slideProperties": {"layoutObjectId": "layout_TITLE"},
                    "pageElements": [
                        {
                            "objectId": "shape001",
                            "size": {"width": {"magnitude": 100}, "height": {"magnitude": 50}},
                            "transform": {},
                            "shape": {
                                "shapeType": "TEXT_BOX",
                                "text": {
                                    "textElements": [
                                        {"textRun": {"content": "Title Text"}}
                                    ]
                                }
                            }
                        }
                    ]
                },
                {
                    "objectId": "slide002",
                    "slideProperties": {"layoutObjectId": "layout_BLANK"},
                    "pageElements": []
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._get_slide(
            {"presentation_id": "pres123", "slide_index": 0},
            sample_oauth_credential
        )

        assert "slide001" in result
        assert "shape001" in result
        assert "Title Text" in result

    def test_validate_oauth_credential_valid(self, sample_oauth_credential):
        """Test validating valid OAuth credential."""
        connector = GoogleSlidesConnector()

        assert connector.validate_oauth_credential(sample_oauth_credential) is True

    def test_validate_oauth_credential_none(self):
        """Test validating None OAuth credential."""
        connector = GoogleSlidesConnector()

        assert connector.validate_oauth_credential(None) is False

    def test_validate_oauth_credential_inactive(self, sample_oauth_credential):
        """Test validating inactive OAuth credential."""
        connector = GoogleSlidesConnector()

        sample_oauth_credential.is_active = False
        assert connector.validate_oauth_credential(sample_oauth_credential) is False


class TestOutlookConnector:
    """Test OutlookConnector class."""

    def test_connector_properties(self):
        """Test Outlook connector properties."""
        connector = OutlookConnector()

        assert connector.display_name == "Microsoft Outlook"
        assert "Outlook" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools_count(self, sample_connector, sample_oauth_credential):
        """Test getting Outlook tools returns correct count."""
        connector = OutlookConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 15

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Outlook tools follow naming convention."""
        connector = OutlookConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("outlook_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        tool_names = [tool.name for tool in tools]
        assert "outlook_list_messages" in tool_names
        assert "outlook_get_message" in tool_names
        assert "outlook_send_message" in tool_names
        assert "outlook_reply_to_message" in tool_names
        assert "outlook_forward_message" in tool_names
        assert "outlook_delete_message" in tool_names
        assert "outlook_move_message" in tool_names
        assert "outlook_list_folders" in tool_names
        assert "outlook_create_folder" in tool_names
        assert "outlook_list_attachments" in tool_names
        assert "outlook_get_attachment" in tool_names
        assert "outlook_create_draft" in tool_names
        assert "outlook_search_messages" in tool_names
        assert "outlook_flag_message" in tool_names
        assert "outlook_list_focused_inbox" in tool_names

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_list_messages(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing messages from inbox."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg001",
                    "subject": "Weekly Report",
                    "from": {
                        "emailAddress": {"name": "Alice", "address": "alice@example.com"}
                    },
                    "toRecipients": [
                        {"emailAddress": {"name": "Bob", "address": "bob@example.com"}}
                    ],
                    "receivedDateTime": "2024-06-15T10:30:00Z",
                    "isRead": False,
                    "hasAttachments": True,
                    "importance": "normal",
                    "bodyPreview": "Please find attached the weekly report.",
                    "flag": {"flagStatus": "notFlagged"},
                    "inferenceClassification": "focused"
                },
                {
                    "id": "msg002",
                    "subject": "Meeting Invitation",
                    "from": {
                        "emailAddress": {"name": "Charlie", "address": "charlie@example.com"}
                    },
                    "toRecipients": [],
                    "receivedDateTime": "2024-06-15T09:00:00Z",
                    "isRead": True,
                    "hasAttachments": False,
                    "importance": "high",
                    "bodyPreview": "Please join the meeting at 3 PM.",
                    "flag": {"flagStatus": "flagged"},
                    "inferenceClassification": "focused"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_messages({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert len(parsed["messages"]) == 2
        assert parsed["messages"][0]["id"] == "msg001"
        assert parsed["messages"][0]["subject"] == "Weekly Report"
        assert parsed["messages"][1]["id"] == "msg002"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_get_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a specific message."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg001",
            "subject": "Weekly Report",
            "from": {
                "emailAddress": {"name": "Alice", "address": "alice@example.com"}
            },
            "toRecipients": [
                {"emailAddress": {"name": "Bob", "address": "bob@example.com"}}
            ],
            "ccRecipients": [],
            "receivedDateTime": "2024-06-15T10:30:00Z",
            "sentDateTime": "2024-06-15T10:29:00Z",
            "isRead": False,
            "hasAttachments": True,
            "importance": "normal",
            "body": {
                "contentType": "HTML",
                "content": "<p>Please find attached the weekly report.</p>"
            },
            "bodyPreview": "Please find attached the weekly report.",
            "flag": {"flagStatus": "notFlagged"},
            "categories": ["Work"],
            "inferenceClassification": "focused",
            "webLink": "https://outlook.office365.com/owa/?ItemID=msg001"
        }
        mock_request.return_value = mock_response

        result = await connector._get_message({"message_id": "msg001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "msg001"
        assert parsed["subject"] == "Weekly Report"
        assert parsed["from"]["address"] == "alice@example.com"
        assert parsed["body"] == "<p>Please find attached the weekly report.</p>"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_send_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test sending a new email message."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.status_code = 202
        mock_request.return_value = mock_response

        result = await connector._send_message(
            {
                "subject": "Test Email",
                "body": "<p>Hello World</p>",
                "to_recipients": ["bob@example.com"]
            },
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "bob@example.com" in parsed["message"]
        assert parsed["subject"] == "Test Email"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_reply_to_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test replying to a message."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.status_code = 202
        mock_request.return_value = mock_response

        result = await connector._reply_to_message(
            {"message_id": "msg001", "comment": "Thanks for the update!"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["message_id"] == "msg001"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_list_folders(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing mail folders."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "folder001",
                    "displayName": "Inbox",
                    "parentFolderId": "root",
                    "childFolderCount": 2,
                    "totalItemCount": 150,
                    "unreadItemCount": 12
                },
                {
                    "id": "folder002",
                    "displayName": "Sent Items",
                    "parentFolderId": "root",
                    "childFolderCount": 0,
                    "totalItemCount": 85,
                    "unreadItemCount": 0
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_folders({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["folders"][0]["display_name"] == "Inbox"
        assert parsed["folders"][0]["total_item_count"] == 150
        assert parsed["folders"][1]["display_name"] == "Sent Items"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_search_messages(self, mock_request, sample_connector, sample_oauth_credential):
        """Test searching messages with $search parameter."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg010",
                    "subject": "Budget Report Q1",
                    "from": {
                        "emailAddress": {"name": "Finance", "address": "finance@example.com"}
                    },
                    "toRecipients": [],
                    "receivedDateTime": "2024-05-01T14:00:00Z",
                    "isRead": True,
                    "hasAttachments": True,
                    "importance": "normal",
                    "bodyPreview": "Q1 budget report attached.",
                    "flag": {"flagStatus": "notFlagged"},
                    "inferenceClassification": "focused"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._search_messages(
            {"query": "budget report"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert parsed["query"] == "budget report"
        assert parsed["messages"][0]["subject"] == "Budget Report Q1"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_create_draft(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a draft email."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "draft001",
            "subject": "Draft Subject",
            "isDraft": True,
            "createdDateTime": "2024-06-15T11:00:00Z",
            "webLink": "https://outlook.office365.com/owa/?ItemID=draft001"
        }
        mock_request.return_value = mock_response

        result = await connector._create_draft(
            {
                "subject": "Draft Subject",
                "body": "<p>Draft body</p>",
                "to_recipients": ["bob@example.com"]
            },
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "draft001"
        assert parsed["subject"] == "Draft Subject"
        assert parsed["is_draft"] is True

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.outlook.OutlookConnector._make_authenticated_request')
    async def test_flag_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test flagging a message via PATCH."""
        connector = OutlookConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg001",
            "subject": "Important Task",
            "flag": {"flagStatus": "flagged"}
        }
        mock_request.return_value = mock_response

        result = await connector._flag_message(
            {"message_id": "msg001", "flag_status": "flagged"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["message_id"] == "msg001"
        assert parsed["flag_status"] == "flagged"

    @pytest.mark.asyncio
    async def test_execute_tool_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = OutlookConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_messages",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = OutlookConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result


class TestTeamsConnector:
    """Test TeamsConnector class."""

    def test_connector_properties(self):
        """Test Teams connector properties."""
        connector = TeamsConnector()

        assert connector.display_name == "Microsoft Teams"
        assert "Teams" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools_count(self, sample_connector, sample_oauth_credential):
        """Test getting Teams tools returns correct count."""
        connector = TeamsConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 15

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Teams tools follow naming convention."""
        connector = TeamsConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("teams_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        tool_names = [tool.name for tool in tools]
        assert "teams_list_teams" in tool_names
        assert "teams_get_team" in tool_names
        assert "teams_list_channels" in tool_names
        assert "teams_get_channel" in tool_names
        assert "teams_list_channel_messages" in tool_names
        assert "teams_get_channel_message" in tool_names
        assert "teams_send_channel_message" in tool_names
        assert "teams_reply_to_message" in tool_names
        assert "teams_list_chats" in tool_names
        assert "teams_list_chat_messages" in tool_names
        assert "teams_send_chat_message" in tool_names
        assert "teams_list_team_members" in tool_names
        assert "teams_search_messages" in tool_names
        assert "teams_list_channel_members" in tool_names

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_list_teams(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing joined teams via GET /me/joinedTeams."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "team001",
                    "displayName": "Engineering",
                    "description": "Engineering team workspace",
                    "isArchived": False,
                    "visibility": "private"
                },
                {
                    "id": "team002",
                    "displayName": "Marketing",
                    "description": "Marketing team workspace",
                    "isArchived": False,
                    "visibility": "public"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_teams({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["teams"][0]["id"] == "team001"
        assert parsed["teams"][0]["displayName"] == "Engineering"
        assert parsed["teams"][1]["displayName"] == "Marketing"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_get_team(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a single team's details."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "team001",
            "displayName": "Engineering",
            "description": "Engineering team workspace",
            "isArchived": False,
            "visibility": "private",
            "webUrl": "https://teams.microsoft.com/l/team/team001",
            "createdDateTime": "2023-01-15T08:00:00Z",
            "memberSettings": {"allowCreateUpdateChannels": True},
            "messagingSettings": {"allowUserEditMessages": True},
            "funSettings": {"allowGiphy": True}
        }
        mock_request.return_value = mock_response

        result = await connector._get_team({"team_id": "team001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "team001"
        assert parsed["displayName"] == "Engineering"
        assert parsed["webUrl"] is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_list_channels(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing channels in a team."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "channel001",
                    "displayName": "General",
                    "description": "General discussion",
                    "membershipType": "standard",
                    "webUrl": "https://teams.microsoft.com/l/channel/channel001",
                    "createdDateTime": "2023-01-15T08:00:00Z"
                },
                {
                    "id": "channel002",
                    "displayName": "Development",
                    "description": "Dev discussions",
                    "membershipType": "standard",
                    "webUrl": "https://teams.microsoft.com/l/channel/channel002",
                    "createdDateTime": "2023-02-01T10:00:00Z"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_channels({"team_id": "team001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["channels"][0]["displayName"] == "General"
        assert parsed["channels"][1]["id"] == "channel002"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_list_channel_messages(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing messages in a channel."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "cmsg001",
                    "createdDateTime": "2024-06-15T12:00:00Z",
                    "lastModifiedDateTime": "2024-06-15T12:00:00Z",
                    "subject": None,
                    "body": {
                        "contentType": "html",
                        "content": "<p>Sprint planning starts tomorrow.</p>"
                    },
                    "from": {
                        "user": {"displayName": "Alice Smith"}
                    },
                    "importance": "normal",
                    "messageType": "message"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_channel_messages(
            {"team_id": "team001", "channel_id": "channel001"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert parsed["messages"][0]["id"] == "cmsg001"
        assert parsed["messages"][0]["from"]["displayName"] == "Alice Smith"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_send_channel_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test sending a message to a channel."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "cmsg002",
            "createdDateTime": "2024-06-15T14:00:00Z",
            "body": {
                "contentType": "html",
                "content": "<p>Hello team!</p>"
            },
            "from": {
                "user": {"displayName": "Test User"}
            }
        }
        mock_request.return_value = mock_response

        result = await connector._send_channel_message(
            {"team_id": "team001", "channel_id": "channel001", "content": "<p>Hello team!</p>"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "cmsg002"
        assert "Hello team!" in parsed["body"]["content"]

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_list_chats(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing user chats."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "chat001",
                    "topic": "Project Alpha",
                    "chatType": "group",
                    "createdDateTime": "2024-01-10T09:00:00Z",
                    "lastUpdatedDateTime": "2024-06-15T16:00:00Z",
                    "webUrl": "https://teams.microsoft.com/l/chat/chat001"
                },
                {
                    "id": "chat002",
                    "topic": None,
                    "chatType": "oneOnOne",
                    "createdDateTime": "2024-03-05T11:00:00Z",
                    "lastUpdatedDateTime": "2024-06-14T08:30:00Z",
                    "webUrl": "https://teams.microsoft.com/l/chat/chat002"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_chats({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["chats"][0]["id"] == "chat001"
        assert parsed["chats"][0]["chatType"] == "group"
        assert parsed["chats"][1]["chatType"] == "oneOnOne"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_send_chat_message(self, mock_request, sample_connector, sample_oauth_credential):
        """Test sending a message in a chat."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "chatmsg001",
            "createdDateTime": "2024-06-15T17:00:00Z",
            "body": {
                "contentType": "text",
                "content": "Hey, can we sync up?"
            },
            "from": {
                "user": {"displayName": "Test User"}
            }
        }
        mock_request.return_value = mock_response

        result = await connector._send_chat_message(
            {"chat_id": "chat001", "content": "Hey, can we sync up?", "content_type": "text"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "chatmsg001"
        assert "sync up" in parsed["body"]["content"]

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.teams.TeamsConnector._make_authenticated_request')
    async def test_list_team_members(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing members of a team."""
        connector = TeamsConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "member001",
                    "displayName": "Alice Smith",
                    "email": "alice@example.com",
                    "roles": ["owner"],
                    "userId": "user001"
                },
                {
                    "id": "member002",
                    "displayName": "Bob Jones",
                    "email": "bob@example.com",
                    "roles": ["member"],
                    "userId": "user002"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_team_members(
            {"team_id": "team001"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["members"][0]["displayName"] == "Alice Smith"
        assert parsed["members"][0]["roles"] == ["owner"]
        assert parsed["members"][1]["email"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_execute_tool_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = TeamsConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_teams",
            {},
            None
        )

        assert "Invalid or expired" in result


class TestExcelConnector:
    """Test ExcelConnector class."""

    def test_connector_properties(self):
        """Test Excel connector properties."""
        connector = ExcelConnector()

        assert connector.display_name == "Microsoft Excel"
        assert "Excel" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools_count(self, sample_connector, sample_oauth_credential):
        """Test getting Excel tools returns correct count."""
        connector = ExcelConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 14

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Excel tools follow naming convention."""
        connector = ExcelConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("excel_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        tool_names = [tool.name for tool in tools]
        assert "excel_list_workbooks" in tool_names
        assert "excel_get_workbook" in tool_names
        assert "excel_list_worksheets" in tool_names
        assert "excel_read_range" in tool_names
        assert "excel_write_range" in tool_names
        assert "excel_append_rows" in tool_names
        assert "excel_clear_range" in tool_names
        assert "excel_create_workbook" in tool_names
        assert "excel_add_worksheet" in tool_names
        assert "excel_delete_worksheet" in tool_names
        assert "excel_list_tables" in tool_names
        assert "excel_create_table" in tool_names
        assert "excel_get_used_range" in tool_names
        assert "excel_run_formula" in tool_names

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_list_workbooks(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing workbooks via OneDrive search."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "wb001",
                    "name": "Budget_2024.xlsx",
                    "size": 45056,
                    "lastModifiedDateTime": "2024-06-01T09:30:00Z",
                    "webUrl": "https://onedrive.live.com/edit.aspx?cid=wb001",
                    "file": {
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    }
                },
                {
                    "id": "wb002",
                    "name": "Inventory.xlsx",
                    "size": 102400,
                    "lastModifiedDateTime": "2024-05-20T14:00:00Z",
                    "webUrl": "https://onedrive.live.com/edit.aspx?cid=wb002",
                    "file": {
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_workbooks({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["workbooks"][0]["id"] == "wb001"
        assert parsed["workbooks"][0]["name"] == "Budget_2024.xlsx"
        assert parsed["workbooks"][1]["name"] == "Inventory.xlsx"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_get_workbook(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting workbook metadata."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "wb001",
            "name": "Budget_2024.xlsx",
            "size": 45056,
            "createdDateTime": "2024-01-10T08:00:00Z",
            "lastModifiedDateTime": "2024-06-01T09:30:00Z",
            "webUrl": "https://onedrive.live.com/edit.aspx?cid=wb001",
            "createdBy": {"user": {"displayName": "Alice Smith"}},
            "lastModifiedBy": {"user": {"displayName": "Bob Jones"}}
        }
        mock_request.return_value = mock_response

        result = await connector._get_workbook({"item_id": "wb001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "wb001"
        assert parsed["name"] == "Budget_2024.xlsx"
        assert parsed["created_by"] == "Alice Smith"
        assert parsed["last_modified_by"] == "Bob Jones"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_list_worksheets(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing worksheets in a workbook."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "ws001",
                    "name": "Sheet1",
                    "position": 0,
                    "visibility": "Visible"
                },
                {
                    "id": "ws002",
                    "name": "Summary",
                    "position": 1,
                    "visibility": "Visible"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_worksheets({"item_id": "wb001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["worksheets"][0]["name"] == "Sheet1"
        assert parsed["worksheets"][1]["name"] == "Summary"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_read_range(self, mock_request, sample_connector, sample_oauth_credential):
        """Test reading a cell range from a worksheet."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "address": "Sheet1!A1:C3",
            "rowCount": 3,
            "columnCount": 3,
            "values": [
                ["Name", "Age", "City"],
                ["Alice", 30, "New York"],
                ["Bob", 25, "Boston"]
            ],
            "formulas": [
                ["Name", "Age", "City"],
                ["Alice", 30, "New York"],
                ["Bob", 25, "Boston"]
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._read_range(
            {"item_id": "wb001", "worksheet": "Sheet1", "range": "A1:C3"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["address"] == "Sheet1!A1:C3"
        assert parsed["row_count"] == 3
        assert parsed["column_count"] == 3
        assert parsed["values"][0] == ["Name", "Age", "City"]
        assert parsed["values"][1][0] == "Alice"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_write_range(self, mock_request, sample_connector, sample_oauth_credential):
        """Test writing values to a cell range."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "address": "Sheet1!A1:B2",
            "rowCount": 2,
            "columnCount": 2
        }
        mock_request.return_value = mock_response

        result = await connector._write_range(
            {
                "item_id": "wb001",
                "worksheet": "Sheet1",
                "range": "A1:B2",
                "values": [["Name", "Age"], ["Charlie", 28]]
            },
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["address"] == "Sheet1!A1:B2"
        assert parsed["row_count"] == 2
        assert parsed["column_count"] == 2

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_append_rows(self, mock_request, sample_connector, sample_oauth_credential):
        """Test appending rows to a table."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "index": 5,
            "values": [["Dave", 35, "Chicago"]]
        }
        mock_request.return_value = mock_response

        result = await connector._append_rows(
            {
                "item_id": "wb001",
                "table_name": "EmployeeTable",
                "values": [["Dave", 35, "Chicago"]]
            },
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["index"] == 5
        assert parsed["values"][0][0] == "Dave"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_create_workbook(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a new workbook via PUT."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "wb_new001",
            "name": "NewWorkbook.xlsx",
            "webUrl": "https://onedrive.live.com/edit.aspx?cid=wb_new001",
            "size": 8192,
            "createdDateTime": "2024-06-15T18:00:00Z"
        }
        mock_request.return_value = mock_response

        result = await connector._create_workbook(
            {"filename": "NewWorkbook.xlsx"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "wb_new001"
        assert parsed["name"] == "NewWorkbook.xlsx"
        assert parsed["web_url"] is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_add_worksheet(self, mock_request, sample_connector, sample_oauth_credential):
        """Test adding a worksheet to a workbook."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ws_new001",
            "name": "Q3 Data",
            "position": 2,
            "visibility": "Visible"
        }
        mock_request.return_value = mock_response

        result = await connector._add_worksheet(
            {"item_id": "wb001", "name": "Q3 Data"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "ws_new001"
        assert parsed["name"] == "Q3 Data"
        assert parsed["position"] == 2

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.excel.ExcelConnector._make_authenticated_request')
    async def test_list_tables(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing tables in a workbook."""
        connector = ExcelConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "tbl001",
                    "name": "EmployeeTable",
                    "showHeaders": True,
                    "showTotals": False,
                    "style": "TableStyleMedium2"
                },
                {
                    "id": "tbl002",
                    "name": "SalesTable",
                    "showHeaders": True,
                    "showTotals": True,
                    "style": "TableStyleLight1"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_tables({"item_id": "wb001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["tables"][0]["name"] == "EmployeeTable"
        assert parsed["tables"][1]["show_totals"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = ExcelConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_workbooks",
            {},
            None
        )

        assert "Invalid or expired" in result


class TestPowerPointConnector:
    """Test PowerPointConnector class."""

    def test_connector_properties(self):
        """Test PowerPoint connector properties."""
        connector = PowerPointConnector()

        assert connector.display_name == "Microsoft PowerPoint"
        assert "PowerPoint" in connector.description
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_get_tools_count(self, sample_connector, sample_oauth_credential):
        """Test getting PowerPoint tools returns correct count."""
        connector = PowerPointConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 10

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all PowerPoint tools follow naming convention."""
        connector = PowerPointConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("powerpoint_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

        tool_names = [tool.name for tool in tools]
        assert "powerpoint_list_presentations" in tool_names
        assert "powerpoint_get_presentation" in tool_names
        assert "powerpoint_get_slide_content" in tool_names
        assert "powerpoint_create_presentation" in tool_names
        assert "powerpoint_export_pdf" in tool_names
        assert "powerpoint_upload_presentation" in tool_names
        assert "powerpoint_list_slides" in tool_names
        assert "powerpoint_copy_presentation" in tool_names
        assert "powerpoint_move_presentation" in tool_names
        assert "powerpoint_delete_presentation" in tool_names

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_list_presentations(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing PowerPoint presentations via OneDrive search."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "ppt001",
                    "name": "Q2 Review.pptx",
                    "size": 2048000,
                    "createdDateTime": "2024-04-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-06-10T15:30:00Z",
                    "webUrl": "https://onedrive.live.com/edit.aspx?cid=ppt001",
                    "parentReference": {"path": "/drive/root:/Presentations"}
                },
                {
                    "id": "ppt002",
                    "name": "Product Launch.pptx",
                    "size": 5120000,
                    "createdDateTime": "2024-05-15T09:00:00Z",
                    "lastModifiedDateTime": "2024-06-14T11:00:00Z",
                    "webUrl": "https://onedrive.live.com/edit.aspx?cid=ppt002",
                    "parentReference": {"path": "/drive/root:/Presentations"}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_presentations({}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["count"] == 2
        assert parsed["presentations"][0]["id"] == "ppt001"
        assert parsed["presentations"][0]["name"] == "Q2 Review.pptx"
        assert parsed["presentations"][1]["name"] == "Product Launch.pptx"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_get_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting presentation metadata."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ppt001",
            "name": "Q2 Review.pptx",
            "size": 2048000,
            "file": {"mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
            "createdDateTime": "2024-04-01T10:00:00Z",
            "lastModifiedDateTime": "2024-06-10T15:30:00Z",
            "webUrl": "https://onedrive.live.com/edit.aspx?cid=ppt001",
            "createdBy": {"user": {"displayName": "Alice Smith"}},
            "lastModifiedBy": {"user": {"displayName": "Bob Jones"}},
            "parentReference": {"path": "/drive/root:/Presentations"}
        }
        mock_request.return_value = mock_response

        result = await connector._get_presentation({"item_id": "ppt001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "ppt001"
        assert parsed["name"] == "Q2 Review.pptx"
        assert parsed["created_by"] == "Alice Smith"
        assert parsed["modified_by"] == "Bob Jones"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_list_slides(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing slide thumbnails for a presentation."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "0",
                    "small": {
                        "url": "https://thumb.example.com/slide1_small.png",
                        "width": 176,
                        "height": 132
                    },
                    "medium": {
                        "url": "https://thumb.example.com/slide1_medium.png",
                        "width": 800,
                        "height": 600
                    },
                    "large": {
                        "url": "https://thumb.example.com/slide1_large.png",
                        "width": 1600,
                        "height": 1200
                    }
                },
                {
                    "id": "1",
                    "small": {
                        "url": "https://thumb.example.com/slide2_small.png",
                        "width": 176,
                        "height": 132
                    },
                    "medium": {
                        "url": "https://thumb.example.com/slide2_medium.png",
                        "width": 800,
                        "height": 600
                    },
                    "large": {
                        "url": "https://thumb.example.com/slide2_large.png",
                        "width": 1600,
                        "height": 1200
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_slides({"item_id": "ppt001"}, sample_oauth_credential)

        import json
        parsed = json.loads(result)
        assert parsed["slide_count"] == 2
        assert parsed["slides"][0]["slide_number"] == 1
        assert "url" in parsed["slides"][0]["medium"]
        assert parsed["slides"][1]["slide_number"] == 2

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_copy_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test copying a presentation."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.headers = {"Location": "https://graph.microsoft.com/v1.0/monitor/copy_op_001"}
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        result = await connector._copy_presentation(
            {"item_id": "ppt001", "new_name": "Copy of Q2 Review.pptx"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["status"] == "accepted"
        assert parsed["new_name"] == "Copy of Q2 Review.pptx"
        assert parsed["item_id"] == "ppt001"

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_move_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test moving a presentation to a different folder."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ppt001",
            "name": "Q2 Review.pptx",
            "webUrl": "https://onedrive.live.com/edit.aspx?cid=ppt001",
            "parentReference": {"path": "/drive/root:/Archive"},
            "lastModifiedDateTime": "2024-06-15T20:00:00Z"
        }
        mock_request.return_value = mock_response

        result = await connector._move_presentation(
            {"item_id": "ppt001", "destination_folder_id": "folder_archive"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["id"] == "ppt001"
        assert parsed["name"] == "Q2 Review.pptx"
        assert "/Archive" in parsed["new_parent_path"]

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.powerpoint.PowerPointConnector._make_authenticated_request')
    async def test_delete_presentation(self, mock_request, sample_connector, sample_oauth_credential):
        """Test deleting a presentation."""
        connector = PowerPointConnector()

        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        result = await connector._delete_presentation(
            {"item_id": "ppt001"},
            sample_oauth_credential
        )

        import json
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["item_id"] == "ppt001"
        assert "deleted" in parsed["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = PowerPointConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_presentations",
            {},
            None
        )

        assert "Invalid or expired" in result


class TestConfluenceConnector:
    """Test ConfluenceConnector class."""

    def test_properties(self):
        """Test Confluence connector properties."""
        connector = ConfluenceConnector()

        assert connector.display_name == "Confluence"
        assert connector.requires_oauth is True
        assert connector.name == "confluence"

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector, sample_oauth_credential):
        """Test Confluence tool count."""
        connector = ConfluenceConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 15

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Confluence tools are correctly prefixed."""
        connector = ConfluenceConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("confluence_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_list_spaces(self, mock_request, sample_oauth_credential):
        """Test listing Confluence spaces."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "123",
                    "key": "DEV",
                    "name": "Development",
                    "type": "global",
                    "status": "current",
                    "description": {}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_spaces("fake-cloud-id", {}, sample_oauth_credential)

        assert "DEV" in result
        assert "Development" in result
        assert "123" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_get_page(self, mock_request, sample_oauth_credential):
        """Test getting a Confluence page by ID."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "456",
            "title": "Architecture Overview",
            "status": "current",
            "body": {
                "storage": {
                    "value": "<p>Page content here</p>"
                }
            },
            "version": {"number": 3}
        }
        mock_request.return_value = mock_response

        result = await connector._get_page("fake-cloud-id", {"page_id": "456"}, sample_oauth_credential)

        assert "456" in result
        assert "Architecture Overview" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_create_page(self, mock_request, sample_oauth_credential):
        """Test creating a Confluence page."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "456",
            "title": "New Page"
        }
        mock_request.return_value = mock_response

        result = await connector._create_page(
            "fake-cloud-id",
            {"space_id": "123", "title": "New Page", "body": "<p>Content</p>"},
            sample_oauth_credential
        )

        assert "456" in result
        assert "New Page" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_search_content(self, mock_request, sample_oauth_credential):
        """Test searching Confluence content via CQL."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "totalSize": 1,
            "results": [
                {
                    "title": "Found",
                    "content": {
                        "id": "789",
                        "type": "page",
                        "status": "current",
                        "space": {"key": "DEV"}
                    },
                    "excerpt": "matched text",
                    "lastModified": "2024-01-01T00:00:00Z",
                    "url": "/wiki/page/789"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._search_content(
            "fake-cloud-id",
            {"cql": "type=page AND text~'architecture'"},
            sample_oauth_credential
        )

        assert "Found" in result
        assert "789" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_update_page(self, mock_request, sample_oauth_credential):
        """Test updating a Confluence page."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "456",
            "title": "Updated Page",
            "version": {"number": 4}
        }
        mock_request.return_value = mock_response

        result = await connector._update_page(
            "fake-cloud-id",
            {"page_id": "456", "title": "Updated Page", "body": "<p>New</p>", "version_number": 3},
            sample_oauth_credential
        )

        assert "456" in result
        assert "Updated Page" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_get_page_children(self, mock_request, sample_oauth_credential):
        """Test getting child pages."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "child1",
                    "title": "Child Page 1",
                    "status": "current",
                    "spaceId": "123",
                    "version": {"number": 1}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._get_page_children(
            "fake-cloud-id",
            {"page_id": "456"},
            sample_oauth_credential
        )

        assert "child1" in result
        assert "Child Page 1" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.confluence.ConfluenceConnector._make_authenticated_request')
    async def test_add_comment(self, mock_request, sample_oauth_credential):
        """Test adding a comment to a page."""
        connector = ConfluenceConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "comment1",
            "status": "current",
            "body": {"storage": {"value": "<p>Great work!</p>"}}
        }
        mock_request.return_value = mock_response

        result = await connector._add_comment(
            "fake-cloud-id",
            {"page_id": "456", "body": "<p>Great work!</p>"},
            sample_oauth_credential
        )

        assert "comment1" in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = ConfluenceConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_spaces",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = ConfluenceConnector()

        with patch.object(connector, '_get_cloud_id', return_value='fake-cloud-id'):
            result = await connector.execute_tool(
                sample_connector,
                "unknown_tool",
                {},
                sample_oauth_credential
            )

        assert "Unknown tool" in result


class TestGitLabConnector:
    """Test GitLabConnector class."""

    def test_properties(self):
        """Test GitLab connector properties."""
        connector = GitLabConnector()

        assert connector.display_name == "GitLab"
        assert connector.requires_oauth is True
        assert connector.name == "gitlab"

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector, sample_oauth_credential):
        """Test GitLab tool count."""
        connector = GitLabConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 23

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all GitLab tools are correctly prefixed."""
        connector = GitLabConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("gitlab_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_list_projects(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing GitLab projects."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "name": "My Project",
                "path_with_namespace": "group/project",
                "description": "A test project",
                "visibility": "private",
                "web_url": "https://gitlab.com/group/project",
                "default_branch": "main",
                "last_activity_at": "2024-01-01T00:00:00Z"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_projects(sample_connector, {}, sample_oauth_credential)

        assert "My Project" in result
        assert "group/project" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_get_project(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting GitLab project details."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 1,
            "name": "My Project",
            "path_with_namespace": "group/project",
            "description": "A test project",
            "visibility": "private",
            "web_url": "https://gitlab.com/group/project"
        }
        mock_request.return_value = mock_response

        result = await connector._get_project(
            sample_connector,
            {"project_id": "1"},
            sample_oauth_credential
        )

        assert "My Project" in result
        assert "group/project" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_list_merge_requests(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing GitLab merge requests."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "iid": 42,
                "title": "Add feature",
                "state": "opened",
                "author": {"username": "dev1"},
                "source_branch": "feature",
                "target_branch": "main",
                "created_at": "2024-01-01T00:00:00Z",
                "web_url": "https://gitlab.com/group/project/-/merge_requests/42"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_merge_requests(
            sample_connector,
            {"project_id": "1"},
            sample_oauth_credential
        )

        assert "Add feature" in result
        assert "42" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_get_merge_request(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting a specific merge request."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "iid": 42,
            "title": "Add feature",
            "state": "opened",
            "description": "Feature description",
            "author": {"username": "dev1"},
            "source_branch": "feature",
            "target_branch": "main"
        }
        mock_request.return_value = mock_response

        result = await connector._get_merge_request(
            sample_connector,
            {"project_id": "1", "merge_request_iid": 42},
            sample_oauth_credential
        )

        assert "Add feature" in result
        assert "42" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_list_issues(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing GitLab issues."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "iid": 10,
                "title": "Fix bug",
                "state": "opened",
                "author": {"username": "dev1"},
                "labels": ["bug"],
                "created_at": "2024-01-01T00:00:00Z",
                "web_url": "https://gitlab.com/group/project/-/issues/10"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_issues(
            sample_connector,
            {"project_id": "1"},
            sample_oauth_credential
        )

        assert "Fix bug" in result
        assert "10" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_create_issue(self, mock_request, sample_connector, sample_oauth_credential):
        """Test creating a GitLab issue."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "iid": 11,
            "title": "New Issue",
            "state": "opened",
            "web_url": "https://gitlab.com/group/project/-/issues/11",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        mock_request.return_value = mock_response

        result = await connector._create_issue(
            sample_connector,
            {"project_id": "1", "title": "New Issue"},
            sample_oauth_credential
        )

        assert "New Issue" in result
        assert "11" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_list_pipelines(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing GitLab pipelines."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 100,
                "status": "success",
                "ref": "main",
                "sha": "abc123",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "web_url": "https://gitlab.com/group/project/-/pipelines/100"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_pipelines(
            sample_connector,
            {"project_id": "1"},
            sample_oauth_credential
        )

        assert "100" in result
        assert "success" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_get_file(self, mock_request, sample_connector, sample_oauth_credential):
        """Test getting file content from GitLab repository."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "content": "cHJpbnQoImhlbGxvIik=",
            "encoding": "base64",
            "file_name": "test.py",
            "file_path": "test.py",
            "size": 14,
            "ref": "main",
            "last_commit_id": "abc123"
        }
        mock_request.return_value = mock_response

        result = await connector._get_file(
            sample_connector,
            {"project_id": "1", "file_path": "test.py"},
            sample_oauth_credential
        )

        assert "test.py" in result
        # Base64 "cHJpbnQoImhlbGxvIik=" decodes to 'print("hello")'
        # In JSON output, inner double quotes are escaped as \"
        assert 'print(\\"hello\\")' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.gitlab.GitLabConnector._make_authenticated_request')
    async def test_list_commits(self, mock_request, sample_connector, sample_oauth_credential):
        """Test listing GitLab commits."""
        connector = GitLabConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "abc123def456",
                "short_id": "abc123d",
                "title": "Initial commit",
                "message": "Initial commit\n",
                "author_name": "Dev User",
                "author_email": "dev@example.com",
                "authored_date": "2024-01-01T00:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "web_url": "https://gitlab.com/group/project/-/commit/abc123"
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_commits(
            sample_connector,
            {"project_id": "1"},
            sample_oauth_credential
        )

        assert "Initial commit" in result
        assert "abc123def456" in result
        assert "Dev User" in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = GitLabConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_projects",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = GitLabConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result


class TestBitbucketConnector:
    """Test BitbucketConnector class."""

    def test_properties(self):
        """Test Bitbucket connector properties."""
        connector = BitbucketConnector()

        assert connector.display_name == "Bitbucket"
        assert connector.requires_oauth is True
        assert connector.name == "bitbucket"

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector, sample_oauth_credential):
        """Test Bitbucket tool count."""
        connector = BitbucketConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 19

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Bitbucket tools are correctly prefixed."""
        connector = BitbucketConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("bitbucket_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_list_repositories(self, mock_request, sample_oauth_credential):
        """Test listing Bitbucket repositories."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "size": 1,
            "page": 1,
            "pagelen": 25,
            "values": [
                {
                    "slug": "my-repo",
                    "full_name": "my-workspace/my-repo",
                    "name": "My Repo",
                    "description": "A test repo",
                    "is_private": True,
                    "scm": "git",
                    "updated_on": "2024-01-01T00:00:00Z",
                    "language": "python",
                    "mainbranch": {"name": "main"}
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_repositories(
            {"workspace": "my-workspace"},
            sample_oauth_credential
        )

        assert "my-repo" in result
        assert "My Repo" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_get_repository(self, mock_request, sample_oauth_credential):
        """Test getting Bitbucket repository details."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "slug": "my-repo",
            "full_name": "my-workspace/my-repo",
            "name": "My Repo",
            "description": "A test repo",
            "is_private": True,
            "scm": "git"
        }
        mock_request.return_value = mock_response

        result = await connector._get_repository(
            {"workspace": "my-workspace", "repo_slug": "my-repo"},
            sample_oauth_credential
        )

        assert "my-repo" in result
        assert "My Repo" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_list_pull_requests(self, mock_request, sample_oauth_credential):
        """Test listing Bitbucket pull requests."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "id": 1,
                    "title": "Add feature",
                    "state": "OPEN",
                    "author": {"display_name": "Dev User"},
                    "source": {"branch": {"name": "feature"}},
                    "destination": {"branch": {"name": "main"}},
                    "created_on": "2024-01-01T00:00:00Z",
                    "updated_on": "2024-01-01T00:00:00Z",
                    "comment_count": 2,
                    "task_count": 0
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_pull_requests(
            {"workspace": "my-workspace", "repo_slug": "my-repo"},
            sample_oauth_credential
        )

        assert "Add feature" in result
        assert "OPEN" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_create_pull_request(self, mock_request, sample_oauth_credential):
        """Test creating a Bitbucket pull request."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 2,
            "title": "New PR",
            "state": "OPEN",
            "source": {"branch": {"name": "feature"}},
            "destination": {"branch": {"name": "main"}},
            "author": {"display_name": "Dev User"},
            "created_on": "2024-01-01T00:00:00Z",
            "links": {"html": {"href": "https://bitbucket.org/ws/repo/pull-requests/2"}}
        }
        mock_request.return_value = mock_response

        result = await connector._create_pull_request(
            {"workspace": "my-workspace", "repo_slug": "my-repo", "title": "New PR", "source_branch": "feature"},
            sample_oauth_credential
        )

        assert "New PR" in result
        assert "created successfully" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_list_issues(self, mock_request, sample_oauth_credential):
        """Test listing Bitbucket issues."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "id": 1,
                    "title": "Bug report",
                    "state": "open",
                    "kind": "bug",
                    "priority": "major",
                    "reporter": {"display_name": "Reporter"},
                    "created_on": "2024-01-01T00:00:00Z"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_issues(
            {"workspace": "my-workspace", "repo_slug": "my-repo"},
            sample_oauth_credential
        )

        assert "Bug report" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_list_branches(self, mock_request, sample_oauth_credential):
        """Test listing Bitbucket branches."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "name": "main",
                    "default_merge_strategy": "merge_commit",
                    "target": {
                        "hash": "abc123",
                        "date": "2024-01-01T00:00:00Z",
                        "message": "Initial commit",
                        "author": {"raw": "Dev <dev@example.com>"}
                    }
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_branches(
            {"workspace": "my-workspace", "repo_slug": "my-repo"},
            sample_oauth_credential
        )

        assert "main" in result
        assert "abc123" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_list_workspaces(self, mock_request, sample_oauth_credential):
        """Test listing Bitbucket workspaces."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "uuid": "{ws-uuid}",
                    "slug": "my-workspace",
                    "name": "My Workspace",
                    "is_private": False,
                    "created_on": "2024-01-01T00:00:00Z"
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await connector._list_workspaces({}, sample_oauth_credential)

        assert "my-workspace" in result
        assert "My Workspace" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.bitbucket.BitbucketConnector._make_authenticated_request')
    async def test_get_diff(self, mock_request, sample_oauth_credential):
        """Test getting pull request diff (returns plain text, not JSON)."""
        connector = BitbucketConnector()

        mock_response = Mock()
        mock_response.text = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        mock_request.return_value = mock_response

        result = await connector._get_diff(
            {"workspace": "my-workspace", "repo_slug": "my-repo", "pull_request_id": 1},
            sample_oauth_credential
        )

        assert "diff --git" in result
        assert "+new" in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = BitbucketConnector()

        result = await connector.execute_tool(
            sample_connector,
            "list_repositories",
            {},
            None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = BitbucketConnector()

        result = await connector.execute_tool(
            sample_connector,
            "unknown_tool",
            {},
            sample_oauth_credential
        )

        assert "Unknown tool" in result


class TestLinearConnector:
    """Test LinearConnector class."""

    def test_properties(self):
        """Test Linear connector properties."""
        connector = LinearConnector()

        assert connector.display_name == "Linear"
        assert connector.requires_oauth is True
        assert connector.name == "linear"

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector, sample_oauth_credential):
        """Test Linear tool count."""
        connector = LinearConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 19

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Linear tools are correctly prefixed."""
        connector = LinearConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("linear_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_list_issues(self, mock_get_client, sample_oauth_credential):
        """Test listing Linear issues."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {
                "id": "issue-1",
                "identifier": "ENG-1",
                "title": "Fix login bug",
                "priority": 2,
                "priorityLabel": "High",
                "state": {"id": "state-1", "name": "In Progress", "color": "#f00"},
                "assignee": {"id": "user-1", "name": "Dev", "email": "dev@example.com"},
                "team": {"id": "team-1", "name": "Engineering", "key": "ENG"},
            }
        ]
        mock_get_client.return_value = mock_client

        result = await connector._list_issues({}, sample_oauth_credential)

        assert "Fix login bug" in result
        assert "ENG-1" in result
        mock_client.collect_connection.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_get_issue(self, mock_get_client, sample_oauth_credential):
        """Test getting a single Linear issue."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issue": {
                "id": "issue-1",
                "identifier": "ENG-1",
                "title": "Fix login bug",
                "priority": 2,
                "priorityLabel": "High",
                "state": {"id": "state-1", "name": "Done"},
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._get_issue({"id": "issue-1"}, sample_oauth_credential)

        assert "Fix login bug" in result
        assert "ENG-1" in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_create_issue(self, mock_get_client, sample_oauth_credential):
        """Test creating a Linear issue."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue-new",
                    "identifier": "ENG-42",
                    "title": "New feature",
                    "url": "https://linear.app/team/ENG-42",
                    "state": {"id": "s1", "name": "Backlog"},
                    "team": {"id": "team-1", "name": "Engineering", "key": "ENG"},
                }
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._create_issue(
            {"title": "New feature", "teamId": "team-1", "priority": 3},
            sample_oauth_credential,
        )

        assert "New feature" in result
        assert "ENG-42" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_update_issue(self, mock_get_client, sample_oauth_credential):
        """Test updating a Linear issue."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue-1",
                    "identifier": "ENG-1",
                    "title": "Updated title",
                    "state": {"id": "s2", "name": "In Progress"},
                }
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._update_issue(
            {"id": "issue-1", "title": "Updated title"},
            sample_oauth_credential,
        )

        assert "Updated title" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_search_issues(self, mock_get_client, sample_oauth_credential):
        """Test searching Linear issues."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {"id": "issue-1", "identifier": "ENG-1", "title": "Login bug"},
        ]
        mock_get_client.return_value = mock_client

        result = await connector._search_issues(
            {"query": "login"}, sample_oauth_credential
        )

        assert "Login bug" in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_archive_issue(self, mock_get_client, sample_oauth_credential):
        """Test archiving a Linear issue."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issueArchive": {"success": True}
        }
        mock_get_client.return_value = mock_client

        result = await connector._archive_issue(
            {"id": "issue-1"}, sample_oauth_credential
        )

        assert '"archived": true' in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_list_teams(self, mock_get_client, sample_oauth_credential):
        """Test listing Linear teams."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {"id": "team-1", "name": "Engineering", "key": "ENG"},
            {"id": "team-2", "name": "Product", "key": "PRD"},
        ]
        mock_get_client.return_value = mock_client

        result = await connector._list_teams({}, sample_oauth_credential)

        assert "Engineering" in result
        assert "Product" in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_list_projects(self, mock_get_client, sample_oauth_credential):
        """Test listing Linear projects."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {
                "id": "proj-1",
                "name": "Q1 Roadmap",
                "state": "started",
                "progress": 0.45,
                "teams": {"nodes": [{"id": "team-1", "name": "Eng", "key": "ENG"}]},
            },
        ]
        mock_get_client.return_value = mock_client

        result = await connector._list_projects({}, sample_oauth_credential)

        assert "Q1 Roadmap" in result

    @pytest.mark.asyncio
    @patch.object(LinearConnector, '_get_client')
    async def test_add_comment(self, mock_get_client, sample_oauth_credential):
        """Test adding a comment to a Linear issue."""
        connector = LinearConnector()

        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "commentCreate": {
                "success": True,
                "comment": {
                    "id": "comment-1",
                    "body": "Looks good!",
                    "url": "https://linear.app/...",
                    "createdAt": "2024-01-15T10:00:00Z",
                    "user": {"id": "user-1", "name": "Dev", "email": "dev@example.com"},
                }
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._add_comment(
            {"issueId": "issue-1", "body": "Looks good!"},
            sample_oauth_credential,
        )

        assert "Looks good!" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = LinearConnector()

        result = await connector.execute_tool(
            sample_connector, "list_issues", {}, None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = LinearConnector()

        result = await connector.execute_tool(
            sample_connector, "nonexistent_tool", {}, sample_oauth_credential
        )

        assert "Unknown tool" in result


class TestDiscordConnector:
    """Test DiscordConnector class."""

    def test_properties(self):
        """Test Discord connector properties."""
        connector = DiscordConnector()

        assert connector.display_name == "Discord"
        assert connector.requires_oauth is True
        assert connector.name == "discord"

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector, sample_oauth_credential):
        """Test Discord tool count."""
        connector = DiscordConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        assert len(tools) == 15

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector, sample_oauth_credential):
        """Test that all Discord tools are correctly prefixed."""
        connector = DiscordConnector()

        tools = await connector.get_tools(sample_connector, sample_oauth_credential)

        for tool in tools:
            assert tool.name.startswith("discord_")
            assert isinstance(tool, types.Tool)
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_guilds(self, mock_request, sample_oauth_credential):
        """Test listing Discord guilds."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "123456", "name": "My Server", "icon": "abc", "owner": True},
            {"id": "789012", "name": "Another Server", "icon": None, "owner": False},
        ]
        mock_request.return_value = mock_response

        result = await connector._list_guilds({}, sample_oauth_credential)

        assert "My Server" in result
        assert "Another Server" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_get_guild(self, mock_request, sample_oauth_credential):
        """Test getting Discord guild details."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "123456",
            "name": "My Server",
            "description": "A test server",
            "approximate_member_count": 50,
            "approximate_presence_count": 10,
        }
        mock_request.return_value = mock_response

        result = await connector._get_guild(
            {"guild_id": "123456"}, sample_oauth_credential
        )

        assert "My Server" in result
        assert "123456" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_channels(self, mock_request, sample_oauth_credential):
        """Test listing Discord channels."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "ch-1", "name": "general", "type": 0, "position": 0},
            {"id": "ch-2", "name": "random", "type": 0, "position": 1},
        ]
        mock_request.return_value = mock_response

        result = await connector._list_channels(
            {"guild_id": "123456"}, sample_oauth_credential
        )

        assert "general" in result
        assert "random" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_messages(self, mock_request, sample_oauth_credential):
        """Test listing Discord messages."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "msg-1",
                "content": "Hello world",
                "author": {"id": "user-1", "username": "dev"},
                "timestamp": "2024-01-15T10:00:00Z",
            }
        ]
        mock_request.return_value = mock_response

        result = await connector._list_messages(
            {"channel_id": "ch-1", "limit": 10}, sample_oauth_credential
        )

        assert "Hello world" in result
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["params"]["limit"] == 10

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_send_message(self, mock_request, sample_oauth_credential):
        """Test sending a Discord message."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "msg-new",
            "content": "Test message",
            "author": {"id": "bot-1", "username": "bot"},
        }
        mock_request.return_value = mock_response

        result = await connector._send_message(
            {"channel_id": "ch-1", "content": "Test message"},
            sample_oauth_credential,
        )

        assert "Test message" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_delete_message(self, mock_request, sample_oauth_credential):
        """Test deleting a Discord message (204 No Content response)."""
        connector = DiscordConnector()

        mock_request.return_value = Mock()

        result = await connector._delete_message(
            {"channel_id": "ch-1", "message_id": "msg-1"},
            sample_oauth_credential,
        )

        assert "Message deleted successfully" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_add_reaction(self, mock_request, sample_oauth_credential):
        """Test adding a reaction (204 No Content response)."""
        connector = DiscordConnector()

        mock_request.return_value = Mock()

        result = await connector._add_reaction(
            {"channel_id": "ch-1", "message_id": "msg-1", "emoji": "%F0%9F%91%8D"},
            sample_oauth_credential,
        )

        assert "Reaction added successfully" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_guild_members(self, mock_request, sample_oauth_credential):
        """Test listing guild members with limit clamping."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"user": {"id": "u1", "username": "dev1"}, "nick": "Developer"},
        ]
        mock_request.return_value = mock_response

        result = await connector._list_guild_members(
            {"guild_id": "123456", "limit": 5000},
            sample_oauth_credential,
        )

        assert "dev1" in result
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["params"]["limit"] == 1000

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_search_messages(self, mock_request, sample_oauth_credential):
        """Test searching Discord messages."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [
                [{"id": "msg-1", "content": "Found this bug", "author": {"username": "dev"}}]
            ],
            "total_results": 1,
        }
        mock_request.return_value = mock_response

        result = await connector._search_messages(
            {"guild_id": "123456", "query": "bug"},
            sample_oauth_credential,
        )

        assert "Found this bug" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_create_thread(self, mock_request, sample_oauth_credential):
        """Test creating a Discord thread."""
        connector = DiscordConnector()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "thread-1",
            "name": "Discussion Thread",
            "type": 11,
            "parent_id": "ch-1",
        }
        mock_request.return_value = mock_response

        result = await connector._create_thread(
            {"channel_id": "ch-1", "message_id": "msg-1", "name": "Discussion Thread"},
            sample_oauth_credential,
        )

        assert "Discussion Thread" in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        """Test executing tool with no OAuth credentials returns error."""
        connector = DiscordConnector()

        result = await connector.execute_tool(
            sample_connector, "list_guilds", {}, None
        )

        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        """Test executing unknown tool returns error."""
        connector = DiscordConnector()

        result = await connector.execute_tool(
            sample_connector, "nonexistent_tool", {}, sample_oauth_credential
        )

        assert "Unknown tool" in result


class TestLinearConnector:
    """Test LinearConnector class.

    Linear uses a GraphQL API via GraphQLClient.  We mock _get_client to return
    an AsyncMock client with execute / collect_connection helpers.
    """

    def test_properties(self):
        connector = LinearConnector()
        assert connector.display_name == "Linear"
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector):
        connector = LinearConnector()
        tools = await connector.get_tools(sample_connector)
        assert len(tools) == 19

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector):
        connector = LinearConnector()
        tools = await connector.get_tools(sample_connector)
        names = {t.name for t in tools}
        expected = {
            "linear_list_issues", "linear_get_issue", "linear_create_issue",
            "linear_update_issue", "linear_search_issues", "linear_archive_issue",
            "linear_list_teams", "linear_get_team", "linear_list_projects",
            "linear_get_project", "linear_create_project", "linear_list_cycles",
            "linear_get_cycle", "linear_list_labels", "linear_list_workflow_states",
            "linear_add_comment", "linear_list_comments", "linear_list_users",
            "linear_get_user_by_email",
        }
        assert names == expected

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_list_issues(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {"id": "iss-1", "identifier": "ENG-1", "title": "Fix login bug", "priority": 2, "priorityLabel": "High"}
        ]
        mock_get_client.return_value = mock_client

        result = await connector._list_issues({}, sample_oauth_credential)
        assert "Fix login bug" in result
        assert "ENG-1" in result
        mock_client.collect_connection.assert_called_once()

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_get_issue(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issue": {"id": "iss-1", "identifier": "ENG-1", "title": "Fix login bug", "priority": 2}
        }
        mock_get_client.return_value = mock_client

        result = await connector._get_issue({"id": "iss-1"}, sample_oauth_credential)
        assert "ENG-1" in result
        assert "Fix login bug" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_create_issue(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issueCreate": {
                "success": True,
                "issue": {"id": "iss-2", "identifier": "ENG-2", "title": "New feature", "url": "https://linear.app/issue/ENG-2"}
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._create_issue(
            {"title": "New feature", "teamId": "team-1"}, sample_oauth_credential
        )
        assert "New feature" in result
        assert "ENG-2" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_update_issue(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "issueUpdate": {
                "success": True,
                "issue": {"id": "iss-1", "identifier": "ENG-1", "title": "Updated title"}
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._update_issue(
            {"id": "iss-1", "title": "Updated title"}, sample_oauth_credential
        )
        assert "Updated title" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_search_issues(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {"id": "iss-3", "identifier": "ENG-3", "title": "Login page broken"}
        ]
        mock_get_client.return_value = mock_client

        result = await connector._search_issues({"query": "login"}, sample_oauth_credential)
        assert "Login page broken" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_archive_issue(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {"issueArchive": {"success": True}}
        mock_get_client.return_value = mock_client

        result = await connector._archive_issue({"id": "iss-1"}, sample_oauth_credential)
        assert '"archived": true' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_list_teams(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.collect_connection.return_value = [
            {"id": "team-1", "name": "Engineering", "key": "ENG"}
        ]
        mock_get_client.return_value = mock_client

        result = await connector._list_teams({}, sample_oauth_credential)
        assert "Engineering" in result
        assert "ENG" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_add_comment(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "commentCreate": {
                "success": True,
                "comment": {"id": "cmt-1", "body": "Looks good!", "url": "https://linear.app/comment/cmt-1"}
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._add_comment(
            {"issueId": "iss-1", "body": "Looks good!"}, sample_oauth_credential
        )
        assert "Looks good!" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.linear.LinearConnector._get_client')
    async def test_create_project(self, mock_get_client, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        mock_client = AsyncMock()
        mock_client.execute.return_value = {
            "projectCreate": {
                "success": True,
                "project": {
                    "id": "proj-1", "name": "Q1 Sprint",
                    "teams": {"nodes": [{"id": "team-1", "name": "Engineering", "key": "ENG"}]}
                }
            }
        }
        mock_get_client.return_value = mock_client

        result = await connector._create_project(
            {"name": "Q1 Sprint", "teamIds": ["team-1"]}, sample_oauth_credential
        )
        assert "Q1 Sprint" in result
        assert '"success": true' in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        connector = LinearConnector()
        result = await connector.execute_tool(sample_connector, "list_issues", {}, None)
        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        connector = LinearConnector()
        result = await connector.execute_tool(sample_connector, "unknown_tool", {}, sample_oauth_credential)
        assert "Unknown tool" in result


class TestDiscordConnector:
    """Test DiscordConnector class.

    Discord uses REST API v10 via _make_authenticated_request.
    """

    def test_properties(self):
        connector = DiscordConnector()
        assert connector.display_name == "Discord"
        assert connector.requires_oauth is True

    @pytest.mark.asyncio
    async def test_tool_count(self, sample_connector):
        connector = DiscordConnector()
        tools = await connector.get_tools(sample_connector)
        assert len(tools) == 15

    @pytest.mark.asyncio
    async def test_tool_names(self, sample_connector):
        connector = DiscordConnector()
        tools = await connector.get_tools(sample_connector)
        names = {t.name for t in tools}
        expected = {
            "discord_list_guilds", "discord_get_guild", "discord_list_channels",
            "discord_get_channel", "discord_list_messages", "discord_send_message",
            "discord_edit_message", "discord_delete_message", "discord_list_guild_members",
            "discord_search_messages", "discord_list_threads", "discord_create_thread",
            "discord_add_reaction", "discord_list_roles", "discord_get_user",
        }
        assert names == expected

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_guilds(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "111", "name": "My Server", "icon": "abc123", "owner": True}
        ]
        mock_request.return_value = mock_response

        result = await connector._list_guilds({}, sample_oauth_credential)
        assert "My Server" in result
        assert "111" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_get_guild(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "111", "name": "My Server", "member_count": 42, "description": "A great server"
        }
        mock_request.return_value = mock_response

        result = await connector._get_guild({"guild_id": "111"}, sample_oauth_credential)
        assert "My Server" in result
        assert "42" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_channels(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "222", "name": "general", "type": 0, "position": 0}
        ]
        mock_request.return_value = mock_response

        result = await connector._list_channels({"guild_id": "111"}, sample_oauth_credential)
        assert "general" in result
        assert "222" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_send_message(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "333", "content": "Hello world!", "author": {"id": "444", "username": "bot"}
        }
        mock_request.return_value = mock_response

        result = await connector._send_message(
            {"channel_id": "222", "content": "Hello world!"}, sample_oauth_credential
        )
        assert "Hello world!" in result
        assert "333" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_delete_message(self, mock_request, sample_oauth_credential):
        """delete_message returns synthetic success JSON (204 No Content)."""
        connector = DiscordConnector()
        mock_request.return_value = Mock()  # 204 — no json needed

        result = await connector._delete_message(
            {"channel_id": "222", "message_id": "333"}, sample_oauth_credential
        )
        assert "deleted successfully" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_guild_members(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = [
            {"user": {"id": "444", "username": "alice"}, "nick": "Alice", "roles": ["555"]}
        ]
        mock_request.return_value = mock_response

        result = await connector._list_guild_members({"guild_id": "111"}, sample_oauth_credential)
        assert "alice" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_create_thread(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "666", "name": "Bug Discussion", "type": 11, "owner_id": "444"
        }
        mock_request.return_value = mock_response

        result = await connector._create_thread(
            {"channel_id": "222", "message_id": "333", "name": "Bug Discussion"},
            sample_oauth_credential
        )
        assert "Bug Discussion" in result
        assert "666" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_add_reaction(self, mock_request, sample_oauth_credential):
        """add_reaction returns synthetic success JSON (204 No Content)."""
        connector = DiscordConnector()
        mock_request.return_value = Mock()

        result = await connector._add_reaction(
            {"channel_id": "222", "message_id": "333", "emoji": "👍"},
            sample_oauth_credential
        )
        assert "Reaction added successfully" in result

    @pytest.mark.asyncio
    @patch('sage_mcp.connectors.discord.DiscordConnector._make_authenticated_request')
    async def test_list_roles(self, mock_request, sample_oauth_credential):
        connector = DiscordConnector()
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "777", "name": "Admin", "permissions": "8", "color": 16711680}
        ]
        mock_request.return_value = mock_response

        result = await connector._list_roles({"guild_id": "111"}, sample_oauth_credential)
        assert "Admin" in result
        assert "777" in result

    @pytest.mark.asyncio
    async def test_no_credentials(self, sample_connector):
        connector = DiscordConnector()
        result = await connector.execute_tool(sample_connector, "list_guilds", {}, None)
        assert "Invalid or expired" in result

    @pytest.mark.asyncio
    async def test_unknown_tool(self, sample_connector, sample_oauth_credential):
        connector = DiscordConnector()
        result = await connector.execute_tool(sample_connector, "unknown_tool", {}, sample_oauth_credential)
        assert "Unknown tool" in result
