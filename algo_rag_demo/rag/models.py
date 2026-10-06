from typing import Optional

from pydantic import BaseModel


class RetrievalResult(BaseModel):
    score: float
    case_id: str
    chunk_id: str
    chunk_type: str
    text: str
    module: str
    final_status: str
    source: str
    case_path: Optional[str] = None

