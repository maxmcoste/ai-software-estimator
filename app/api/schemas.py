from pydantic import BaseModel
from typing import Optional


class EstimateJobResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    progress_message: str
    error_detail: Optional[str] = None
