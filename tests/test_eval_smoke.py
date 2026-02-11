from __future__ import annotations

from pathlib import Path

from app.eval.runner import run_eval
from app.eval.schemas import EvalRunReport


def test_eval_runner_smoke_mock_mode(tmp_path: Path) -> None:
    out_path = tmp_path / "report.json"
    report = run_eval(
        dataset_path="eval/golden.jsonl",
        out_path=str(out_path),
        mock=True,
        max_cases=1,
        cleanup=True,
    )

    # Schema validation (also checks it's JSON-serializable).
    loaded = EvalRunReport.model_validate_json(out_path.read_text(encoding="utf-8"))
    assert loaded.summary.total_cases == 1
    assert len(loaded.results) == 1

    # Basic groundedness: we should have at least one citation.
    assert len(loaded.results[0].citations_document_names) >= 1

    # Ensure we compute a pass/fail outcome.
    assert loaded.results[0].metrics.passed in {True, False}

