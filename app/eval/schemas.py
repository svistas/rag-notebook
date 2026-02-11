from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvalDoc(BaseModel):
    filename: str
    content: str


class EvalExpectations(BaseModel):
    must_include_keywords: list[str] = Field(default_factory=list)
    must_cite_document_names: list[str] = Field(default_factory=list)
    must_not_include_keywords: list[str] = Field(default_factory=list)
    allow_unsure: bool = False


class EvalCase(BaseModel):
    case_id: str
    docs: list[EvalDoc]
    question: str
    expects: EvalExpectations


class EvalLatency(BaseModel):
    embed_query_ms: float
    retrieval_ms: float
    generation_ms: float
    total_ms: float


class EvalCaseMetrics(BaseModel):
    retrieval_hit: bool
    citations_match: bool
    keyword_coverage: bool
    no_forbidden_keywords: bool
    abstention_ok: bool

    passed: bool


class EvalCaseResult(BaseModel):
    case_id: str
    question: str
    expected: EvalExpectations

    answer: str
    citations_document_names: list[str]
    retrieved_document_names: list[str]

    metrics: EvalCaseMetrics
    latency: EvalLatency


class EvalRunSummary(BaseModel):
    dataset_path: str
    started_at: datetime
    finished_at: datetime
    total_cases: int
    passed_cases: int
    pass_rate: float


class EvalRunReport(BaseModel):
    summary: EvalRunSummary
    results: list[EvalCaseResult]

