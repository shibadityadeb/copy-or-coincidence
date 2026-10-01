"""One JSONL row per agent-turn (field guide §9). Rows are append-only; never edit a written row."""
import hashlib
from typing import Optional

from pydantic import BaseModel, Field


class Trial(BaseModel):
    # identity
    trial_id: str
    experiment_id: str
    run_id: str
    task_id: str
    sample_index: int                     # k-th independent sample (Layer 0) or r-th run (protocols)
    # item
    family: str
    template_id: str
    error_cause_by_construction: str
    difficulty_param: Optional[float]
    item_correct: str
    item_lure: Optional[str]
    # model + settings
    agent_id: str
    model: str
    model_revision: str
    quantization: str
    dtype: str
    backend: str
    framework_version: str
    enable_thinking: bool
    structured_output: bool = False      # decoding constrained to the answer JSON schema
    role: str = "solver"
    prompt_version: str
    prompt_hash: str
    seed: int
    temperature: float
    top_p: float
    max_tokens: int
    # protocol
    protocol: str = "independent"
    condition: str = "A"                  # A = independent (see guide §8 table)
    interaction_round: int = 0
    previous_agent_output_available: bool = False
    peer_trial_ids: list[str] = Field(default_factory=list)
    peer_content_shown: Optional[str] = None
    retrieved_context_id: Optional[str] = None
    # output + grading
    raw_output: str
    final: Optional[str | float | int | bool] = None
    parse_ok: bool
    parse_how: str
    answer_norm: Optional[str]
    normalizer_version: str
    checker_version: str
    correct: bool
    error_class: str
    lure_hit: bool
    first_error_step: Optional[int] = None
    confidence: Optional[float]
    n_steps: Optional[int]
    # cost + provenance
    prompt_tokens: int
    output_tokens: int
    truncated: bool
    latency_ms: float
    batch_id: str
    batch_position: int
    timestamp: str


def stable_seed(*parts: str) -> int:
    """Per-trial seed from its identity, so a rerun reproduces it regardless of order or batching."""
    return int.from_bytes(hashlib.sha256("|".join(parts).encode()).digest()[:4], "big") & 0x7FFFFFFF
