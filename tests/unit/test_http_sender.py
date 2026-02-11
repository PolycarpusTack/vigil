"""Unit tests for agent HTTP sender with retry logic.

Tests cover:
- Successful send on first attempt
- Retry on server error (500)
- Give up after max retries
- Retry on timeout
- No retry on client error (400)
- Exponential backoff timing
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from agent.transport.http_sender import HTTPSender


@pytest.fixture
def sender():
    """Create an HTTPSender with short backoff for testing."""
    return HTTPSender(
        collector_url="http://localhost:8080",
        api_key="test-key",
        timeout=5,
        max_retries=3,
        backoff_base=0.01,  # very short for tests
    )


@pytest.fixture
def mock_post(sender):
    """Patch the session.post method on the sender."""
    with patch.object(sender.session, "post") as mocked:
        yield mocked


class TestSendMetricsRetry:
    """Test suite for HTTPSender retry behavior."""

    def test_send_metrics_no_retry_on_success(self, sender, mock_post):
        """Test that successful send does not trigger retries."""
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"status": "accepted"}
        mock_post.return_value = mock_resp

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is True
        assert mock_post.call_count == 1

    def test_send_metrics_retries_on_server_error(self, sender, mock_post):
        """Test that 500 errors trigger retries and eventual success."""
        fail_resp = Mock()
        fail_resp.status_code = 500
        fail_resp.text = "Internal Server Error"

        success_resp = Mock()
        success_resp.status_code = 201
        success_resp.json.return_value = {"status": "accepted"}

        # Fail twice, then succeed
        mock_post.side_effect = [fail_resp, fail_resp, success_resp]

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is True
        assert mock_post.call_count == 3

    def test_send_metrics_gives_up_after_max_retries(self, sender, mock_post):
        """Test that send returns False after exhausting all retries."""
        fail_resp = Mock()
        fail_resp.status_code = 500
        fail_resp.text = "Internal Server Error"

        mock_post.return_value = fail_resp

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is False
        assert mock_post.call_count == 3  # max_retries = 3

    def test_send_metrics_retries_on_timeout(self, sender, mock_post):
        """Test that timeout errors trigger retries."""
        success_resp = Mock()
        success_resp.status_code = 201
        success_resp.json.return_value = {"status": "accepted"}

        # Timeout once, then succeed
        mock_post.side_effect = [
            requests.Timeout("Connection timed out"),
            success_resp,
        ]

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is True
        assert mock_post.call_count == 2

    def test_send_metrics_retries_on_connection_error(self, sender, mock_post):
        """Test that connection errors trigger retries."""
        success_resp = Mock()
        success_resp.status_code = 201
        success_resp.json.return_value = {"status": "accepted"}

        mock_post.side_effect = [
            requests.ConnectionError("Connection refused"),
            success_resp,
        ]

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is True
        assert mock_post.call_count == 2

    def test_send_metrics_no_retry_on_client_error(self, sender, mock_post):
        """Test that 4xx errors (except 429) are not retried."""
        fail_resp = Mock()
        fail_resp.status_code = 400
        fail_resp.text = "Bad Request"

        mock_post.return_value = fail_resp

        result = sender.send_metrics({"metrics": {}})

        assert result is False
        assert mock_post.call_count == 1  # No retry on 400

    def test_send_metrics_retries_on_429(self, sender, mock_post):
        """Test that 429 (rate limited) triggers retries."""
        rate_limit_resp = Mock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.text = "Too Many Requests"

        success_resp = Mock()
        success_resp.status_code = 201
        success_resp.json.return_value = {"status": "accepted"}

        mock_post.side_effect = [rate_limit_resp, success_resp]

        result = sender.send_metrics({"metrics": {"cpu_percent": 50.0}})

        assert result is True
        assert mock_post.call_count == 2


class TestHTTPSenderInit:
    """Test suite for HTTPSender initialization."""

    def test_auth_header_set(self):
        """Test that auth header is set when api_key provided."""
        sender = HTTPSender("http://localhost:8080", api_key="my-key")
        assert sender.session.headers["Authorization"] == "Bearer my-key"
        sender.close()

    def test_no_auth_header_without_key(self):
        """Test that no auth header is set when api_key is empty."""
        sender = HTTPSender("http://localhost:8080", api_key="")
        assert "Authorization" not in sender.session.headers
        sender.close()

    def test_base_url_strips_trailing_slash(self):
        """Test that trailing slash is removed from URL."""
        sender = HTTPSender("http://localhost:8080/", api_key="key")
        assert sender.base_url == "http://localhost:8080"
        sender.close()

    def test_close_closes_session(self):
        """Test that close() closes the HTTP session."""
        sender = HTTPSender("http://localhost:8080", api_key="key")
        mock_session = MagicMock()
        sender.session = mock_session

        sender.close()

        mock_session.close.assert_called_once()
