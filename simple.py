import asyncio
import csv
import io
import time
from typing import Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, model_serializer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://hospital-directory.onrender.com"
MAX_CSV_HOSPITALS = 20
MAX_CONCURRENT_REQUESTS = 20

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HospitalResult(BaseModel):
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str  # "created_and_activated" | "failed"
    error: Optional[str] = None


class BulkResponse(BaseModel):
    batch_id: UUID
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: list[HospitalResult]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

app = FastAPI(title="Hospital Bulk Processor")


@app.post("/hospitals/bulk", response_model=BulkResponse)
async def bulk_create_hospitals(file: UploadFile = File(...)) -> BulkResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))

    if not {"name", "address"}.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail="CSV must have 'name' and 'address' columns.")

    rows = list(reader)

    if len(rows) == 0:
        raise HTTPException(status_code=400, detail="CSV has no data rows.")

    if len(rows) > MAX_CSV_HOSPITALS:
        raise HTTPException(status_code=400, detail=f"CSV exceeds maximum of {MAX_CSV_HOSPITALS} hospitals.")

    return await process_bulk(rows)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

async def process_bulk(rows: list[dict]) -> BulkResponse:
    batch_id = uuid4()
    start = time.time()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        tasks = [
            _create_hospital(client, row_num=i + 1, row=row, batch_id=batch_id, semaphore=semaphore)
            for i, row in enumerate(rows)
        ]
        results = await asyncio.gather(*tasks)

        failed = [r for r in results if r.status == "failed"]
        activated = False

        if not failed:
            activate_resp = await client.patch(f"/hospitals/batch/{batch_id}/activate")
            if activate_resp.status_code == 200:
                activated = True
                for r in results:
                    r.status = "created_and_activated"

    elapsed = round(time.time() - start, 3)

    return BulkResponse(
        batch_id=batch_id,
        total_hospitals=len(rows),
        processed_hospitals=len(rows) - len(failed),
        failed_hospitals=len(failed),
        processing_time_seconds=elapsed,
        batch_activated=activated,
        hospitals=results,
    )


async def _create_hospital(
    client: httpx.AsyncClient, row_num: int, row: dict, batch_id: UUID, semaphore: asyncio.Semaphore
) -> HospitalResult:
    name = row.get("name", "").strip()
    address = row.get("address", "").strip()
    phone = row.get("phone", "").strip() or None

    if not name or not address:
        return HospitalResult(row=row_num, name=name or "(empty)", status="failed", error="Missing name or address") # type: ignore

    payload = {"name": name, "address": address, "phone": phone, "creation_batch_id": str(batch_id)}

    try:
        async with semaphore:
            resp = await client.post("/hospitals/", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return HospitalResult(row=row_num, hospital_id=data["id"], name=name, status="created")
    except Exception as e:
        return HospitalResult(row=row_num, name=name, status="failed", error=str(e)) # type: ignore
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple:app", host="0.0.0.0", port=8000, reload=True)


## Run code with
# python simple.py
# uvicorn simple:app --reload
