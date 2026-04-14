import asyncio
from uuid import uuid4
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from simple import app, process_bulk, _create_hospital

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_csv(*rows: str) -> bytes:
    """Build a CSV bytes object. First arg is always the header row."""
    return "\n".join(rows).encode("utf-8")


VALID_CSV = make_csv(
    "name,address,phone",
    "City Hospital,123 Main St,1111111111",
    "Apollo,Jubilee Hills,2222222222",
)

# ---------------------------------------------------------------------------
# Router tests — CSV validation (no external calls needed)
# ---------------------------------------------------------------------------

def test_rejects_non_csv_extension():
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.txt", VALID_CSV, "text/plain")},
    )
    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_rejects_missing_required_columns():
    bad_csv = make_csv("hospital_name,location", "Apollo,Hyderabad")
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", bad_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "name" in response.json()["detail"].lower()


def test_rejects_empty_csv():
    empty_csv = make_csv("name,address,phone")  # header only, no rows
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", empty_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "no data rows" in response.json()["detail"].lower()


def test_rejects_csv_exceeding_max_rows():
    rows = ["name,address"] + [f"Hospital {i},{i} Street" for i in range(21)]
    big_csv = make_csv(*rows)
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", big_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "20" in response.json()["detail"]


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


# ---------------------------------------------------------------------------
# Helper tests — _create_hospital directly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_hospital_missing_name_returns_failed():
    semaphore = asyncio.Semaphore(1)
    mock_client = AsyncMock()

    result = await _create_hospital(
        client=mock_client,
        row_num=1,
        row={"name": "", "address": "Some Addr", "phone": "1111111111"},
        batch_id=uuid4(),
        semaphore=semaphore,
    )

    assert result.status == "failed"
    assert result.error is not None and "missing" in result.error.lower()
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

    result = await _create_hospital(
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

    result = await _create_hospital(
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

    result = await _create_hospital(
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