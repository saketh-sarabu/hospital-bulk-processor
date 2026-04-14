from fastapi.testclient import TestClient

from app.main import app

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
