import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.service import process_bulk

# ---------------------------------------------------------------------------
# Service tests — process_bulk with mocked HTTP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_bulk_all_success():
    rows = [
        {"name": "Hospital A", "address": "Addr A", "phone": "111"},
        {"name": "Hospital B", "address": "Addr B", "phone": ""},
        {"name": "Hospital C", "address": "Addr C"},
    ]

    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.side_effect = [{"id": 1}, {"id": 2}, {"id": 3}]  # matches 3 rows
    create_response.raise_for_status = MagicMock()

    activate_response = MagicMock()
    activate_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=create_response)
        mock_client.patch = AsyncMock(return_value=activate_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await process_bulk(rows)

    assert result.total_hospitals == 3
    assert result.processed_hospitals == 3
    assert result.failed_hospitals == 0
    assert result.batch_activated is True
    assert all(h.status == "created_and_activated" for h in result.hospitals)


@pytest.mark.asyncio
async def test_process_bulk_partial_failure_does_not_activate():
    rows = [
        {"name": "Good Hospital", "address": "Good Addr"},
        {"name": "", "address": "Good Addr 2"},  # will fail validation in helper
    ]

    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {"id": 10}
    create_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=create_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await process_bulk(rows)

    assert result.failed_hospitals == 1
    assert result.batch_activated is False
    mock_client.patch.assert_not_called()
