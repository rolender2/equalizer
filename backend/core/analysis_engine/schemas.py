from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class TranscriptSegment(BaseModel):
    speaker: str
    timestamp: float = Field(default=0.0)
    text: str

class TacticSignal(BaseModel):
    category: Literal[
        "ANCHORING",
        "URGENCY",
        "AUTHORITY",
        "FRAMING",
        "COMMITMENT_TRAP",
        "CONCESSION",
        "BUNDLING",
        "PAYMENT_DEFLECTION",
        "LOSS_AVERSION",
        "SOCIAL_PROOF",
        "NONE",
    ]
    subtype: str = Field(description="Specific technique used (e.g., 'deadline', 'policy_shield')", default="none")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    headline: str = Field(description="Short, human-readable headline", default="Signal detected")
    why: str = Field(description="Concise explanation of why it matters", default="")
    best_question: str = Field(description="Single best next question for the user", default="")
    evidence: str
    timestamp: float = Field(default=0.0)
    options: List[str] = Field(default_factory=list, max_length=3)
    message: str = Field(description="Short, neutral observation", default="Signal detected")

    # Backwards compatibility alias if needed, or we just update usages
    @property
    def tactic(self):
        return self.category

class ImprovementSummary(BaseModel):
    strong_move: str
    missed_opportunity: str
    improvement_tip: str
    expanded_insights: Optional[List[str]] = None

class AnalysisResult(BaseModel):
    signals: List[TacticSignal] = Field(default_factory=list)
    summary: Optional[ImprovementSummary] = None
