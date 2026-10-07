from typing import Any, Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class Conversation(BaseModel):
    conversation_id: str
    task: str
    messages: List[Message]


class EngineeringCase(BaseModel):
    case_id: str = Field(pattern=r"^CASE_[A-Za-z0-9_.-]+$")
    module: str
    task: str
    old_algorithm: Optional[str] = None
    new_algorithm: Optional[str] = None
    constraints: Dict[str, List[str]] = Field(default_factory=dict)
    steps: List[str] = Field(default_factory=list)
    problems: List[Dict[str, str]] = Field(default_factory=list)
    solutions: List[Dict[str, str]] = Field(default_factory=list)
    validation: Dict[str, str] = Field(default_factory=dict)
    final_status: Literal["success", "failed", "partial"]
    reusable_experience: List[str] = Field(default_factory=list)
    source_conversation_id: str


class KnowledgeChunk(BaseModel):
    chunk_id: str
    case_id: str
    chunk_type: str
    text: str
    module: str
    final_status: str
    source: str


class CaseExtractor(Protocol):
    def extract(self, conversation: Conversation) -> EngineeringCase:
        ...


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Convert validated models to plain dictionaries."""
    return model.model_dump()

