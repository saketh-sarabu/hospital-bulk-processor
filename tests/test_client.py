import asyncio
from uuid import uuid4

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.client import create_hospital

# ---------------------------------------------------------------------------
# Helper tests — create_hospital directly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_hospital_missing_name_returns_failed():
    semaphore = asyncio.Semaphore(1)
    mock_client = AsyncMock()

    result = await create_hospital(
        client=mock_client,
        row_num=1,
        row={"name": "", "address": "Some Addr", "phone": "1111111111"},
        batch_id=uuid4(),
        semaphore=semaphore,
    )

    assert result.status == "failed"
    assert result.error is not None and "missing" in result.error.lower() # type: ignore
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_create_hospital_http_error_returns_failed():
    semaphore = asyncio.Semaphore(1)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock()
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await create_hospital(
        client=mock_client,
        row_num=2,
        row={"name": "Test Hospital", "address": "Test Addr", "phone": "1111111111"},
        batch_id=uuid4(),
        semaphore=semaphore,
    )

    assert result.status == "failed"
    assert result.hospital_id is None


@pytest.mark.asyncio
async def test_create_hospital_phone_optional():
    semaphore = asyncio.Semaphore(1)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": 99}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await create_hospital(
        client=mock_client,
        row_num=1,
        row={"name": "No Phone Hospital", "address": "Somewhere", "phone": ""},
        batch_id=uuid4(),
        semaphore=semaphore,
    )

    assert result.status == "created"
    assert result.hospital_id == 99
    call_payload = mock_client.post.call_args.kwargs["json"]
    assert call_payload["phone"] is None


@pytest.mark.asyncio
async def test_create_hospital_no_phone_attr():
    semaphore = asyncio.Semaphore(1)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": 99}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await create_hospital(
        client=mock_client,
        row_num=1,
        row={"name": "No Phone attr Hospital", "address": "Somewhere"},
        batch_id=uuid4(),
        semaphore=semaphore,
    )

    assert result.status == "created"
    assert result.hospital_id == 99
    call_payload = mock_client.post.call_args.kwargs["json"]
    assert call_payload["phone"] is None
