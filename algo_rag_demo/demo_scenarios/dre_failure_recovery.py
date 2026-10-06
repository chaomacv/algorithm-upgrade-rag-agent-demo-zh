from pathlib import Path
from typing import Dict, List

from algo_rag_demo.agent.executor import PlanExecutor
from algo_rag_demo.agent.tool_registry import ToolRegistry, new_run_dir
from algo_rag_demo.rag.retriever import Retriever
from algo_rag_demo.scaffold import reset_demo_project
from algo_rag_demo.utils.jsonio import write_json


DRE_UPGRADE_TASK = "Replace OldDRE with NewLLF while keeping downstream interface compatible"


def run_dre_failure_recovery_demo(provider_name: str, planner, console) -> Dict[str, object]:
    """Run the teaching scenario: fail once, retrieve the error, then repair."""
    # This module owns the demo storyline so CLI and reusable agent code stay small.
    reset_demo_project(mode="old")
    run_dir = new_run_dir("demo-failure")
    tools = ToolRegistry(run_dir)
    retriever = Retriever(provider_name=provider_name)

    console.print("[1/10] Retrieve historical cases for the upgrade task")
    initial_results = retriever.search(DRE_UPGRADE_TASK, top_k=5, module="DRE")
    _print_top_results(console, initial_results)
    initial_plan = planner.plan(DRE_UPGRADE_TASK, initial_results)
    write_json(run_dir / "initial_retrieval.json", _as_jsonable(initial_results))
    write_json(run_dir / "initial_plan.json", initial_plan)

    console.print("[2/10] Execute first plan through controlled executor")
    first_execution = PlanExecutor(tools).execute(direct_replacement_plan())
    write_json(run_dir / "initial_execution.json", first_execution)
    if first_execution["status"] == "success":
        console.print("Unexpected: first execution passed")
    else:
        console.print(f"Executor validation FAIL ({first_execution.get('error')})")

    error_query = build_error_query(first_execution)
    console.print(f'[3/10] Retrieve historical cases for error: "{error_query}"')
    repair_results = retriever.search(error_query, top_k=5, module="DRE")
    _print_top_results(console, repair_results)

    console.print("[4/10] Ask planner for repair plan")
    repair_plan = planner.plan(DRE_UPGRADE_TASK, repair_results)
    _write_repair_run_files(run_dir, repair_results, repair_plan)

    console.print("[5/10] Execute repair plan through controlled executor")
    repair_execution = PlanExecutor(tools).execute(repair_plan)
    write_json(run_dir / "repair_execution.json", repair_execution)

    console.print("[6/10] Running rollback validation")
    validation = repair_execution.get("validation", {})
    validation["rollback"] = _validate_rollback(tools) if repair_execution["status"] == "success" else "not_run"
    report = _finalize(
        console=console,
        run_dir=run_dir,
        cases=_case_ids(repair_results),
        validation=validation,
        modified_files=repair_execution.get("modified_files", []),
    )
    return {"run_dir": str(run_dir), "report": report}


def direct_replacement_plan() -> Dict[str, object]:
    """Build the intentionally unsafe first-attempt plan for the teaching demo."""
    # The plan creates the concrete residual_map failure used for RAG recovery.
    return {
        "task_understanding": {"attempt": "direct replacement without adapter compatibility"},
        "plan": [
            "Directly replace the DRE adapter output with NewLLF output",
            "Switch pipeline config to new_llf",
            "Run validations",
        ],
        "executable_plan": {
            "steps": [
                {
                    "type": "patch",
                    "target": "demo_project/src/modules/dre_adapter.py",
                    "intent": "direct replacement without residual_map compatibility",
                },
                {
                    "type": "patch",
                    "target": "demo_project/config/pipeline.json",
                    "intent": "switch dre_algorithm to new_llf",
                },
                {"type": "validate", "checks": ["interface", "runtime", "algorithm_switch"]},
            ]
        },
    }


def build_error_query(first_execution: Dict[str, object]) -> str:
    """Turn the first failed execution into an error-specific retrieval query."""
    # Error retrieval is the point of the scenario: search with evidence, not vibes.
    return f"DRE interface validation failed {first_execution.get('error', '')} residual_map NewLLF"


def _write_repair_run_files(run_dir: Path, retrieval, plan: Dict[str, object]) -> None:
    """Write the second retrieval and repair plan artifacts."""
    write_json(run_dir / "task.json", {"task": DRE_UPGRADE_TASK})
    write_json(run_dir / "retrieval.json", _as_jsonable(retrieval))
    write_json(run_dir / "plan.json", plan)


def _validate_rollback(tools: ToolRegistry) -> str:
    """Switch to old_dre, verify it runs, then restore the upgraded config."""
    tools.call("write_file", path="config/pipeline.json", content='{\n  "dre_algorithm": "old_dre"\n}\n')
    result = tools.call("verify_algorithm_switch", expected="old_dre")
    tools.call("write_file", path="config/pipeline.json", content='{\n  "dre_algorithm": "new_llf"\n}\n')
    return result["status"]


def _finalize(console, run_dir: Path, cases, validation: Dict[str, str], modified_files) -> Dict[str, object]:
    """Write the final scenario report and print a compact result."""
    write_json(run_dir / "validation.json", validation)
    status = "success" if all(value == "passed" for value in validation.values()) else "failed"
    report = {
        "status": status,
        "task": DRE_UPGRADE_TASK,
        "retrieved_cases": cases,
        "modified_files": modified_files,
        "validation": validation,
    }
    write_json(run_dir / "final_report.json", report)
    console.print("[8/8] Final Result")
    console.print(status.upper())
    console.print(f"Run artifacts: {run_dir}")
    return report


def _print_top_results(console, results) -> None:
    """Print top retrieval hits in the same compact format as the CLI."""
    for idx, item in enumerate(results[:3], 1):
        console.print(f"#{idx} {item.chunk_id} score={item.score}")


def _case_ids(results) -> List[str]:
    """Return stable unique case ids from retrieval results."""
    return list(dict.fromkeys(item.case_id for item in results))


def _as_jsonable(items):
    """Convert pydantic retrieval objects into JSON-serializable dictionaries."""
    return [item.dict() if hasattr(item, "dict") else item for item in items]
