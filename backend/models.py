from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class HospitalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)

class HospitalResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: Optional[str]
    creation_batch_id: str
    active: bool
    created_at: str

class ProcessedHospital(BaseModel):
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str
    error_message: Optional[str] = None

class BulkProcessingResult(BaseModel):
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[ProcessedHospital]