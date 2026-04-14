from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HospitalResult(BaseModel):
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str  # "created_and_activated" | "failed"

    model_config = ConfigDict(extra="allow")    # For extra "error" variable, only when needed


class BulkResponse(BaseModel):
    batch_id: UUID
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: list[HospitalResult]
