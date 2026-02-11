from __future__ import annotations

import argparse

from app.eval.runner import run_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Notebook offline evaluation harness")
    parser.add_argument("--dataset", default="eval/golden.jsonl", help="Path to JSONL dataset")
    parser.add_argument("--out", default="eval/results/latest.json", help="Path to write JSON report")
    parser.add_argument("--mock", action="store_true", help="Use deterministic OpenAI mocks (no network)")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit number of cases to run")
    parser.add_argument("--cleanup", action=argparse.BooleanOptionalAction, default=True, help="Cleanup DB rows and stored files")
    args = parser.parse_args()

    run_eval(
        dataset_path=args.dataset,
        out_path=args.out,
        mock=bool(args.mock),
        max_cases=args.max_cases,
        cleanup=bool(args.cleanup),
    )


if __name__ == "__main__":
    main()

