# API Reference

Base URL (local): `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## POST /hospitals/bulk

Upload a CSV file to create and activate multiple hospital records in one operation.

### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `.csv` file | Yes | CSV with hospital records |

**CSV format:**

```
name,address,phone
City General Hospital,123 Main Street,040-12345678
Apollo Hospitals,Jubilee Hills,040-23456789
```

| Column | Required | Description |
|---|---|---|
| `name` | Yes | Hospital name |
| `address` | Yes | Full address |
| `phone` | No | Phone number (omit or leave blank) |

Constraints:
- File must have `.csv` extension
- Must contain `name` and `address` columns
- Must have at least 1 data row
- Maximum 20 rows per upload

### Response — 200 OK

```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_hospitals": 3,
  "processed_hospitals": 3,
  "failed_hospitals": 0,
  "processing_time_seconds": 1.243,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 101,
      "name": "City General Hospital",
      "status": "created_and_activated"
    },
    {
      "row": 2,
      "hospital_id": 102,
      "name": "Apollo Hospitals",
      "status": "created_and_activated"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `batch_id` | UUID | Unique identifier for this upload batch |
| `total_hospitals` | int | Number of rows in the CSV |
| `processed_hospitals` | int | Rows successfully created in the directory API |
| `failed_hospitals` | int | Rows that failed (validation or API error) |
| `processing_time_seconds` | float | Wall-clock time for the entire operation |
| `batch_activated` | bool | `true` if all hospitals were activated; `false` if any failed |
| `hospitals` | array | Per-row results (see below) |

**Hospital result status values:**

| Status | Meaning |
|---|---|
| `created_and_activated` | Created and batch was activated successfully |
| `created` | Created but batch activation was skipped (partial failure) |
| `failed` | Not created — see `error` field for reason |

Failed rows include an additional `error` string field explaining the failure.

### Response — 400 Bad Request

Returned for any of the following validation failures:

| Condition | Detail message |
|---|---|
| File extension is not `.csv` | `Only .csv files are accepted.` |
| Missing `name` or `address` column | `CSV must have 'name' and 'address' columns.` |
| No data rows | `CSV has no data rows.` |
| More than 20 rows | `CSV exceeds maximum of 20 hospitals.` |

```json
{
  "detail": "CSV has no data rows."
}
```

### Example — curl

```bash
curl -X POST http://localhost:8000/hospitals/bulk \
  -F "file=@sample.csv"
```

### Example — Python (httpx)

```python
import httpx

with open("sample.csv", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/hospitals/bulk",
        files={"file": ("sample.csv", f, "text/csv")},
    )

print(response.json())
```
