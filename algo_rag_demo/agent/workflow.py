import json
from pathlib import Path
from typing import Dict

from algo_rag_demo.rag.prompt_builder import build_prompt
from algo_rag_demo.utils.jsonio import write_json


def _rollback(adapter) -> Dict[str, object]:
    """Record rollback failures so a failed restore never looks successful."""
    try:
        return adapter.rollback()
    except Exception as exc:
        return {"restored": False, "error": str(exc)}


def run_agent(task, retriever, planner, adapter, run_dir: Path,
              repository_facts="", skill="", top_k=5, module=None, max_attempts=3) -> Dict[str, object]:
    """Retrieve, plan, execute, validate, and retry or roll back using actual outcomes."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")
    adapter.checkpoint()
    attempts = []
    query = task
    last_error = ""
    try:
        for number in range(1, max_attempts + 1):
            attempt_dir = run_dir / "attempts" / f"{number:02d}"
            attempt_dir.mkdir(parents=True, exist_ok=True)
            results = retriever.search(query, top_k=top_k, module=module)
            facts = repository_facts + "\n\n" + adapter.facts()
            if last_error:
                facts += "\n\nPREVIOUS VALIDATION / EXECUTION FAILURE:\n" + last_error
            facts += "\n\nALGORITHM REPLACEMENT SKILL:\n" + skill
            write_json(attempt_dir / "retrieval.json", [item.dict() for item in results])
            write_json(attempt_dir / "query.json", {"query": query})
            (attempt_dir / "prompt.md").write_text(build_prompt(task, results, facts), encoding="utf-8")
            try:
                plan = planner.plan(task, results, facts)
                write_json(attempt_dir / "plan.json", plan)
                execution = adapter.execute(plan)
                write_json(attempt_dir / "execution.json", execution)
                validation = adapter.validate()
            except Exception as exc:
                validation = {"passed": False, "error": str(exc), "stage": "planning_or_execution"}
            write_json(attempt_dir / "validation.json", validation)
            attempts.append({"attempt": number, "passed": validation.get("passed") is True,
                             "retrieved_cases": list(dict.fromkeys(item.case_id for item in results))})
            if validation.get("passed") is True:
                report = {"status": "success", "attempts": attempts, "rollback": None}
                write_json(run_dir / "final_report.json", report)
                return report
            last_error = json.dumps(validation, ensure_ascii=False)
            analysis = {"failure": validation, "next_action": "retry" if number < max_attempts else "rollback"}
            write_json(attempt_dir / "error_analysis.json", analysis)
            # Error evidence is embedded and searched again; no fixed repair is injected.
            query = task + "\nValidation failure:\n" + last_error
    except Exception as exc:
        report = {"status": "failed", "attempts": attempts, "error": str(exc),
                  "rollback": _rollback(adapter)}
        write_json(run_dir / "final_report.json", report)
        raise
    rollback = _rollback(adapter)
    report = {"status": "rolled_back" if rollback.get("restored") is True else "rollback_failed",
              "attempts": attempts, "rollback": rollback}
    write_json(run_dir / "final_report.json", report)
    return report
