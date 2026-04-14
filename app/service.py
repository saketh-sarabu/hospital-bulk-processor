import asyncio
import time
from uuid import uuid4

import httpx

from app.client import create_hospital, activate_batch
from app.config import BASE_URL, MAX_CONCURRENT_REQUESTS
from app.schemas import BulkResponse


async def process_bulk(rows: list[dict]) -> BulkResponse:
    """Processes a list of CSV rows by creating and activating hospitals in bulk."""
    batch_id = uuid4()
    start = time.time()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        tasks = [
            create_hospital(client, row_num=i + 1, row=row, batch_id=batch_id, semaphore=semaphore)
            for i, row in enumerate(rows)
        ]
        results = await asyncio.gather(*tasks)

        failed = [r for r in results if r.status == "failed"]
        activated = False

        if not failed:
            activated = await activate_batch(client, batch_id)
            if activated:
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
