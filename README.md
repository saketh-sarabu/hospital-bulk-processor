# Hospital Bulk Processor

A lightweight FastAPI service that accepts a CSV file and bulk-creates hospitals
in the [Hospital Directory API](https://hospital-directory.onrender.com), using
batch processing with automatic activation.

---

## How It Works

1. Upload a CSV file of hospitals via `POST /hospitals/bulk`
2. CSV file is validated and a unique `batch_id` (UUID) is generated
3. All hospitals are created concurrently against the Hospital Directory API, each tagged with the `batch_id`
4. If **all** rows succeed, the batch is activated in one call → hospitals go live
5. A full processing report is returned

```
CSV Upload → Validate → Create (concurrent) → Activate Batch → Response
```


## Project Structure

```
hospital-bulk-processor/
├── app/
│   ├── main.py          # FastAPI app instance
│   ├── config.py        # Env-based configuration
│   ├── schemas.py       # Pydantic models: HospitalResult, BulkResponse
│   ├── router.py        # Route handler + CSV validation
│   ├── service.py       # Bulk processing — orchestration and business logic
│   └── client.py        # Hospital Directory External API calls
├── tests/
│   ├── test_router.py
│   ├── test_service.py
│   └── test_client.py
├── sample.csv
├── .env.example
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```


## Setup & Running

### Using uv (recommended)
[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter the project
git clone https://github.com/saketh-sarabu/hospital-bulk-processor
cd hospital-bulk-processor

# Create virtual environment and install dependencies
uv sync

# Install dev dependencies for testing
uv sync --extra dev

# Copy and configure environment
cp .env.example .env

# Run the server
uv run uvicorn app.main:app --reload
```

### Using pip

```bash
# Clone and enter the project
git clone https://github.com/saketh-sarabu/hospital-bulk-processor
cd hospital-bulk-processor

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app

# Copy and configure environment
cp .env.example .env

# Run the server
uvicorn app.main:app --reload
```

Server will be available at: http://localhost:8000
Interactive docs: http://localhost:8000/docs


## Usage

Upload a CSV file with `name`, `address`, and optional `phone` columns:

```bash
curl -X POST http://localhost:8000/hospitals/bulk -F "file=@sample.csv"
```

A `sample.csv` is included in the repository. Maximum 20 rows per upload.
See [docs/api.md](docs/api.md) for the full request/response reference.


## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `HOSPITAL_API_BASE_URL` | `https://hospital-directory.onrender.com` | Hospital Directory API base URL |
| `MAX_CSV_HOSPITALS` | `20` | Maximum rows allowed per CSV upload |
| `MAX_CONCURRENT_REQUESTS` | `20` | Max parallel requests to Hospital API |

---


## Running Tests

```bash
# uv
uv run pytest tests/

# pip
pytest tests/
```

---


Server will be available at: http://localhost:8000

---


## Documentation

- [API Reference](docs/api.md) — endpoint, request/response schema, error codes
- [Architecture](docs/architecture.md) — module design, workflow, concurrency model
