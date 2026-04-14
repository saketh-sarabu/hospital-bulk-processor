import asyncio
from uuid import UUID

import httpx

from app.schemas import HospitalResult


async def create_hospital(
    client: httpx.AsyncClient, row_num: int, row: dict, batch_id: UUID, semaphore: asyncio.Semaphore
) -> HospitalResult:
    """Creates a single hospital record in the directory API."""
    name = row.get("name", "").strip()
    address = row.get("address", "").strip()
    phone = row.get("phone", "").strip() or None

    if not name or not address:
        return HospitalResult(row=row_num, name=name or "(empty)", status="failed", error="Missing name or address")  # type: ignore

    payload = {"name": name, "address": address, "phone": phone, "creation_batch_id": str(batch_id)}

    try:
        async with semaphore:
            resp = await client.post("/hospitals/", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return HospitalResult(row=row_num, hospital_id=data["id"], name=name, status="created")
    except Exception as e:
        return HospitalResult(row=row_num, name=name, status="failed", error=str(e))  # type: ignore


async def activate_batch(client: httpx.AsyncClient, batch_id: UUID) -> bool:
    """Activates all hospitals in a batch via the directory API."""
    activate_resp = await client.patch(f"/hospitals/batch/{batch_id}/activate")
    return activate_resp.status_code == 200
