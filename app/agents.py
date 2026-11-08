"""Optional reasoning boundary.

This module deliberately returns proposals only. Provider writes and status changes
remain in the FastAPI services after deterministic validation and human approval.
"""
from pydantic import BaseModel, Field

class EvidenceProposal(BaseModel):
    quote: str = Field(min_length=1)
    source_url: str | None = None

class DraftProposal(BaseModel):
    message: str
    evidence: list[EvidenceProposal]
    confidence: float = Field(ge=0, le=1)

def agents_sdk_available() -> bool:
    try:
        import agents  # noqa: F401
        return True
    except ImportError:
        return False

def build_draft_agent():
    """Create a bounded agent only when the optional SDK is installed.

    The caller should pass an output_type=DraftProposal configuration and still
    validate character count, source grounding, and approval before any write.
    """
    if not agents_sdk_available():
        return None
    from agents import Agent
    return Agent(name='Warm Signal Drafting', instructions=(
        'Draft evidence-grounded outreach from supplied source text. '
        'Never invent facts, claims, names, or company details. Return only a typed proposal.'
    ), output_type=DraftProposal)
