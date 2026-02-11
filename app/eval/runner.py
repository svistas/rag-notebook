from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.models import Chunk, ChunkEmbedding, Document, User
from app.db.session import get_engine
from app.eval.schemas import (
    EvalCase,
    EvalCaseMetrics,
    EvalCaseResult,
    EvalLatency,
    EvalRunReport,
    EvalRunSummary,
)
from app.rag.prompting import generate_answer, set_chat_client
from app.rag.retrieval import retrieve_with_debug
from app.rag.embedding import set_embedding_client
from app.rag.query_rewrite import set_rewrite_client
from app.rag.rerank import set_rerank_client
from app.services.auth_service import hash_password
from app.services.document_service import create_document_record, index_document


def load_cases(dataset_path: str) -> list[EvalCase]:
    path = Path(dataset_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    cases: list[EvalCase] = []
    for line in lines:
        if not line.strip():
            continue
        payload = json.loads(line)
        cases.append(EvalCase.model_validate(payload))
    return cases


def _contains_all_keywords(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return all(k.lower() in t for k in keywords)


def _contains_any_keyword(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)


def _abstention_ok(answer: str) -> bool:
    a = answer.lower()
    return ("unsure" in a) or ("not enough" in a) or ("could not find" in a)


def run_eval(
    dataset_path: str,
    out_path: str,
    *,
    mock: bool = False,
    max_cases: int | None = None,
    cleanup: bool = True,
) -> EvalRunReport:
    started_at = datetime.now(timezone.utc)

    # Optional deterministic mode for CI and smoke tests.
    if mock:
        from app.eval.mock_openai import MockOpenAIClient

        client = MockOpenAIClient()
        set_embedding_client(client)
        set_chat_client(client)
        set_rewrite_client(client)
        set_rerank_client(client)

    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    cases = load_cases(dataset_path)
    if max_cases is not None:
        cases = cases[: max_cases]

    results: list[EvalCaseResult] = []

    with SessionLocal() as db:
        for case in cases:
            # Create a fresh temp user per case so document sets never leak across cases.
            user_id = uuid.uuid4()
            user = User(id=user_id, email=f"eval+{user_id}@example.com", password_hash=hash_password("password123"))
            db.add(user)
            db.commit()

            created_doc_ids: list[uuid.UUID] = []
            try:
                t0 = perf_counter()

                for d in case.docs:
                    meta = create_document_record(db=db, user=user, filename=d.filename, content=d.content.encode("utf-8"))
                    created_doc_ids.append(uuid.UUID(meta.id))
                    index_document(db=db, user=user, doc_id=meta.id)

                t_retrieval_start = perf_counter()
                retrieval = retrieve_with_debug(db=db, user=user, user_query=case.question)
                t_retrieval_done = perf_counter()

                answer_resp = generate_answer(query=case.question, chunks=retrieval.final_chunks)
                t_generation_done = perf_counter()

                retrieved_doc_names = [c.document_name for c in retrieval.final_chunks]
                citation_doc_names = [c.document_name for c in answer_resp.citations]

                retrieval_hit = (
                    True
                    if not case.expects.must_cite_document_names
                    else any(name in case.expects.must_cite_document_names for name in retrieved_doc_names)
                )
                citations_match = (
                    True
                    if not case.expects.must_cite_document_names
                    else all(name in citation_doc_names for name in case.expects.must_cite_document_names)
                )
                keyword_coverage = _contains_all_keywords(answer_resp.answer, case.expects.must_include_keywords)
                no_forbidden_keywords = not _contains_any_keyword(answer_resp.answer, case.expects.must_not_include_keywords)
                abstention_ok = True if not case.expects.allow_unsure else _abstention_ok(answer_resp.answer)

                passed = all([retrieval_hit, citations_match, keyword_coverage, no_forbidden_keywords, abstention_ok])

                latency = EvalLatency(
                    embed_query_ms=0.0,
                    retrieval_ms=(t_retrieval_done - t_retrieval_start) * 1000.0,
                    generation_ms=(t_generation_done - t_retrieval_done) * 1000.0,
                    total_ms=(t_generation_done - t0) * 1000.0,
                )

                results.append(
                    EvalCaseResult(
                        case_id=case.case_id,
                        question=case.question,
                        expected=case.expects,
                        answer=answer_resp.answer,
                        citations_document_names=citation_doc_names,
                        retrieved_document_names=retrieved_doc_names,
                        metrics=EvalCaseMetrics(
                            retrieval_hit=retrieval_hit,
                            citations_match=citations_match,
                            keyword_coverage=keyword_coverage,
                            no_forbidden_keywords=no_forbidden_keywords,
                            abstention_ok=abstention_ok,
                            passed=passed,
                        ),
                        latency=latency,
                    )
                )
            finally:
                if cleanup:
                    # Remove stored files for this user.
                    settings = get_settings()
                    user_dir = settings.upload_path / str(user_id)
                    if user_dir.exists():
                        shutil.rmtree(user_dir, ignore_errors=True)

                    for doc_id in created_doc_ids:
                        chunk_ids = db.execute(select(Chunk.id).where(Chunk.document_id == doc_id)).scalars().all()
                        if chunk_ids:
                            db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids)))
                        db.execute(delete(Chunk).where(Chunk.document_id == doc_id))
                        db.execute(delete(Document).where(Document.id == doc_id))

                    db.execute(delete(User).where(User.id == user_id))
                    db.commit()

    finished_at = datetime.now(timezone.utc)
    passed_cases = sum(1 for r in results if r.metrics.passed)
    total_cases = len(results)
    pass_rate = (passed_cases / total_cases) if total_cases else 0.0

    report = EvalRunReport(
        summary=EvalRunSummary(
            dataset_path=dataset_path,
            started_at=started_at,
            finished_at=finished_at,
            total_cases=total_cases,
            passed_cases=passed_cases,
            pass_rate=pass_rate,
        ),
        results=results,
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    if mock:
        # Reset injection so normal app behavior isn't affected in-process.
        set_embedding_client(None)
        set_chat_client(None)
        set_rewrite_client(None)
        set_rerank_client(None)

    return report

