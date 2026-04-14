# Architecture

## Overview

The Hospital Bulk Processor is a FastAPI service that accepts CSV uploads and creates hospital records in the [Hospital Directory API](https://hospital-directory.onrender.com) in bulk. It is intentionally thin — no database, no queue, no state beyond a single HTTP request.

```
Client (HTTP)
    │
    ▼
POST /hospitals/bulk   ← router.py  (validates CSV, calls service)
    │
    ▼
process_bulk()         ← service.py  (generates batch ID, fans out tasks, activates)
    │
    ├── create_hospital() × N  ← client.py  (POST /hospitals/ with semaphore)
    │
    └── activate_batch()       ← client.py  (PATCH /hospitals/batch/{id}/activate)
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `app/config.py` | Central constants: `BASE_URL`, `MAX_CSV_HOSPITALS`, `MAX_CONCURRENT_REQUESTS` |
| `app/schemas.py` | Pydantic I/O models: `HospitalResult`, `BulkResponse` |
| `app/router.py` | HTTP layer — file upload, CSV validation, HTTP 400s |
| `app/service.py` | Business logic — batch ID generation, async fan-out, activate-on-success |
| `app/client.py` | External API calls — `create_hospital()`, `activate_batch()` |
| `app/main.py` | FastAPI app instantiation, router mount |

## Processing Workflow

1. `POST /hospitals/bulk` receives a multipart CSV upload.
2. The router validates: `.csv` extension, `name`/`address` columns, ≥1 row, ≤20 rows.
3. `process_bulk()` generates a UUID batch ID and starts a shared `httpx.AsyncClient`.
4. One `create_hospital()` task is spawned per row. All tasks run concurrently, bounded by `asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)`.
5. If **all** rows succeed, `activate_batch()` is called to flip every hospital to `active=true` atomically.
6. If **any** row fails, activation is skipped and the batch remains inactive in the directory API.
7. A `BulkResponse` is returned with counts, elapsed time, and per-row results.

## Concurrency Model

- Uses `asyncio` + `httpx.AsyncClient` for non-blocking I/O.
- A single `asyncio.Semaphore` caps concurrent outbound requests at `MAX_CONCURRENT_REQUESTS` (default 20, equal to the CSV row limit — effectively unlimited for this constraint).
- All hospital creation tasks are gathered with `asyncio.gather`, so total wall-clock time approaches the slowest single request rather than the sum.

## Error Handling

- Per-row failures are captured inside `create_hospital()` and stored as `status="failed"` — they do not propagate exceptions to `process_bulk()`.
- Activation is all-or-nothing: partial failures prevent the PATCH call entirely.
- The API always returns HTTP 200 with a `BulkResponse` even if some rows failed; only CSV validation issues return HTTP 400.

## External Dependency

The Hospital Directory API (`https://hospital-directory.onrender.com`) is a pre-existing service. This application does not manage its state beyond the batch operations described above.
