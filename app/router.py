import csv
import io
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.config import MAX_CSV_HOSPITALS
from app.schemas import BulkResponse
from app.service import process_bulk

router = APIRouter()


@router.post("/hospitals/bulk", response_model=BulkResponse)
async def bulk_create_hospitals(file: UploadFile = File(...)) -> BulkResponse:
    """
        Validates the uploaded CSV and triggers bulk hospital creation.
        Provide CSV file with name, address and phone[optional].
        Max 20 rows.
    """
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
