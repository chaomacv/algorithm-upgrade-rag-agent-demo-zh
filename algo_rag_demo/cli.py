import argparse
import json
from pathlib import Path
from typing import Dict, List

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - used on minimal servers
    class Console:
        def print(self, value="") -> None:
            """Print plain text when Rich is unavailable."""
            print(value)

    class Table:
        def __init__(self, title: str = "") -> None:
            """Create a minimal table container for fallback output."""
            self.title = title
            self.columns = []
            self.rows = []

        def add_column(self, name: str) -> None:
            """Record one table column name."""
            self.columns.append(name)

        def add_row(self, *values: str) -> None:
            """Record one table row."""
            self.rows.append(values)

        def __str__(self) -> str:
            """Render the fallback table as simple text."""
            lines = [self.title] if self.title else []
            if self.columns:
                lines.append(" | ".join(self.columns))
                lines.append("-" * max(20, len(lines[-1])))
            lines.extend(" | ".join(row) for row in self.rows)
            return "\n".join(lines)

from algo_rag_demo.agent.executor import PlanExecutor
from algo_rag_demo.agent.planner import EvidencePlanner, LLMPlanner, MockPlanner
from algo_rag_demo.agent.tool_registry import ToolRegistry, new_run_dir
from algo_rag_demo.case_pipeline.parser import DeepSeekChatProvider, LLMCaseExtractor, RuleBasedCaseExtractor, extract_case_file
from algo_rag_demo.config import CASE_DIR, DEMO_PROJECT_DIR, EXAMPLES_DIR, INDEX_DIR, RAW_DIR, RUNS_DIR, SKILL_FILE
from algo_rag_demo.demo_scenarios.dre_failure_recovery import run_dre_failure_recovery_demo
from algo_rag_demo.rag.index_builder import build_index, build_index_from_cases
from algo_rag_demo.rag.prompt_builder import build_prompt, load_skill
from algo_rag_demo.rag.retriever import Retriever
from algo_rag_demo.scaffold import reset_demo_project
from algo_rag_demo.utils.jsonio import read_json, write_json

console = Console()


def ensure_index() -> None:
    """Build the mock index if expected index files are missing."""
    # Search commands should work after a fresh checkout.
    if not (INDEX_DIR / "cases.index").exists() or not (INDEX_DIR / "metadata.json").exists():
        build_index("mock")


def _case_output_path(raw_path: Path, case_id: str = None) -> Path:
    """Choose a default output path for an extracted case."""
    # LLM output may later rename the file to match case.case_id.
    if case_id:
        return CASE_DIR / f"{case_id}.json"
    stem = raw_path.stem.replace("conversation_", "").upper()
    return CASE_DIR / f"CASE_{stem}.json"


def _make_case_extractor(args: argparse.Namespace):
    """Create the requested rule-based or DeepSeek case extractor."""
    # DeepSeek settings come from environment variables and optional CLI flags.
    if args.extractor == "deepseek":
        provider = DeepSeekChatProvider(base_url=args.base_url, model=args.model)
        return LLMCaseExtractor(provider)
    return RuleBasedCaseExtractor()


def _make_planner(args: argparse.Namespace):
    """Create the requested mock or DeepSeek-backed planner."""
    # The planner output schema is shared by mock and LLM implementations.
    if getattr(args, "planner", "mock") == "deepseek":
        provider = DeepSeekChatProvider(base_url=args.base_url, model=args.model)
        return LLMPlanner(provider)
    if getattr(args, "planner", "mock") == "evidence":
        return EvidencePlanner()
    return MockPlanner()


def cmd_extract_case(args: argparse.Namespace) -> None:
    """CLI command that extracts one or more raw conversations into cases."""
    # Batch mode processes every synthetic conversation file in examples/data/raw.
    extractor = _make_case_extractor(args)
    if args.all:
        raw_paths = sorted(RAW_DIR.glob("conversation_*.json"))
    else:
        raw_paths = [Path(args.raw) if args.raw else RAW_DIR / "conversation_dre_upgrade.json"]
    for raw_path in raw_paths:
        output_path = Path(args.output) if args.output and len(raw_paths) == 1 else _case_output_path(raw_path)
        case = extract_case_file(raw_path, output_path, extractor)
        final_path = output_path
        if not args.output and output_path.name != f"{case.case_id}.json":
            final_path = CASE_DIR / f"{case.case_id}.json"
            write_json(final_path, case)
        console.print(f"Extracted {case.case_id} -> {final_path}")


def cmd_build_index(args: argparse.Namespace) -> None:
    """CLI command that builds chunks, embeddings, and vector index files."""
    # The provider flag controls mock vs BGE-M3 embeddings.
    cases, chunks, dimension = build_index(args.provider)
    console.print(f"Loaded {cases} cases")
    console.print(f"Generated {chunks} chunks")
    console.print(f"Embedding dimension: {dimension}")
    console.print("FAISS-compatible index built successfully")
    console.print("Saved to outputs/index/cases.index")


def cmd_search(args: argparse.Namespace) -> None:
    """CLI command that retrieves the most relevant knowledge chunks."""
    # Results show chunk-level evidence rather than only case ids.
    ensure_index()
    results = Retriever(provider_name=args.provider).search(args.query, top_k=args.top_k, module=args.module)
    table = Table(title="Retrieval Results")
    table.add_column("Rank")
    table.add_column("Case")
    table.add_column("Chunk")
    table.add_column("Score")
    table.add_column("Text")
    for idx, item in enumerate(results, 1):
        table.add_row(str(idx), item.case_id, item.chunk_type, str(item.score), item.text[:100])
    console.print(table)


def cmd_build_prompt(args: argparse.Namespace) -> None:
    """CLI command that prints the assembled agent prompt."""
    # Prompt inspection helps explain how RAG context is passed to the agent.
    ensure_index()
    results = Retriever(provider_name=args.provider).search(args.task, top_k=5, module="DRE")
    prompt = build_prompt(
        task=args.task,
        retrieved_cases=results,
        skill_text=load_skill(SKILL_FILE),
        repository_facts="demo_project contains a DRE adapter, pipeline config, old algorithm, and new algorithm.",
    )
    console.print(prompt)


def _write_common_run_files(run_dir: Path, task: str, retrieval, plan: Dict[str, object]) -> None:
    """Write shared run artifacts for task, retrieval, and plan."""
    # These artifacts make each demo run auditable.
    write_json(run_dir / "task.json", {"task": task})
    write_json(run_dir / "retrieval.json", [item.dict() if hasattr(item, "dict") else item for item in retrieval])
    write_json(run_dir / "plan.json", plan)


def _run_validations(tools: ToolRegistry, expected: str = "new_llf") -> Dict[str, str]:
    """Run the standard build/interface/runtime/switch validation set."""
    # The switch check proves the new algorithm is actually active.
    build = tools.call("run_build_check")
    interface = tools.call("run_interface_tests")
    runtime = tools.call("run_runtime_tests")
    switch = tools.call("verify_algorithm_switch", expected=expected)
    return {
        "build": build["status"],
        "interface": interface["status"],
        "runtime": runtime["status"],
        "algorithm_switch": switch["status"],
    }


def _case_ids(results) -> List[str]:
    """Return stable unique case ids from retrieval results."""
    # Final reports summarize cases, while detailed chunks stay in retrieval.json.
    return list(dict.fromkeys(item.case_id for item in results))


def _load_task(args: argparse.Namespace) -> str:
    """Load a task from --task or --task-file."""
    # Custom mode supports keeping the task beside user-provided data.
    if getattr(args, "task", None):
        return args.task
    if getattr(args, "task_file", None):
        return Path(args.task_file).read_text(encoding="utf-8").strip()
    raise ValueError("Either --task or --task-file is required.")


def _extract_raw_dir_to_cases(args: argparse.Namespace, output_case_dir: Path) -> Path:
    """Extract every raw conversation in a custom raw directory into run-local cases."""
    # Keeping extracted cases under the run directory avoids mutating user input.
    extractor = _make_case_extractor(args)
    output_case_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = Path(args.raw_dir)
    raw_paths = sorted(raw_dir.glob("*.json"))
    if not raw_paths:
        raise ValueError(f"No raw conversation JSON files found in {raw_dir}")
    for raw_path in raw_paths:
        temporary_path = output_case_dir / f"{raw_path.stem}.json"
        case = extract_case_file(raw_path, temporary_path, extractor)
        final_path = output_case_dir / f"{case.case_id}.json"
        if temporary_path != final_path:
            temporary_path.unlink(missing_ok=True)
        write_json(final_path, case)
    return output_case_dir


def cmd_run_custom(args: argparse.Namespace) -> None:
    """Run the reusable RAG-to-plan workflow on caller-provided cases."""
    # This is the reusable path for reader-provided data. It is intentionally
    # dry-run by default and does not mutate a target repository.
    task = _load_task(args)
    run_dir = new_run_dir("custom")
    case_dir = (
        _extract_raw_dir_to_cases(args, run_dir / "cases")
        if args.raw_dir
        else Path(args.case_dir)
    )
    index_dir = run_dir / "index"
    knowledge_dir = run_dir / "knowledge"
    cases, chunks, dimension = build_index_from_cases(
        provider_name=args.provider,
        case_dir=case_dir,
        knowledge_dir=knowledge_dir,
        index_dir=index_dir,
    )
    results = Retriever(
        index_dir=index_dir,
        provider_name=args.provider,
        case_dir=case_dir,
    ).search(task, top_k=args.top_k, module=args.module)
    repository_facts = (
        Path(args.repository_facts).read_text(encoding="utf-8")
        if args.repository_facts
        else "Custom dry-run mode: no target repository facts were provided."
    )
    prompt = build_prompt(
        task=task,
        retrieved_cases=results,
        skill_text=load_skill(Path(args.skill_file)),
        repository_facts=repository_facts,
    )
    plan = _make_planner(args).plan(task, results)
    write_json(run_dir / "task.json", {"task": task})
    write_json(run_dir / "retrieval.json", [item.dict() if hasattr(item, "dict") else item for item in results])
    write_json(run_dir / "plan.json", plan)
    write_json(
        run_dir / "final_report.json",
        {
            "status": "planned",
            "mode": "custom_dry_run",
            "cases_loaded": cases,
            "chunks_generated": chunks,
            "embedding_dimension": dimension,
            "case_dir": str(case_dir),
            "index_dir": str(index_dir),
            "knowledge_dir": str(knowledge_dir),
            "retrieved_cases": _case_ids(results),
            "note": "Custom mode builds RAG evidence and a plan. Execution requires a project-specific ToolRegistry.",
        },
    )
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    console.print("[custom] Built custom RAG index")
    console.print(f"[custom] Cases: {cases}, chunks: {chunks}, dimension: {dimension}")
    console.print("[custom] Top retrieval")
    for idx, item in enumerate(results, 1):
        console.print(f"#{idx} {item.chunk_id} score={item.score}")
    console.print("[custom] Plan")
    for step in plan["plan"]:
        console.print(f"- {step}")
    console.print(f"[custom] Run artifacts: {run_dir}")


def cmd_demo(args: argparse.Namespace) -> None:
    """CLI command that runs the successful end-to-end demo."""
    # Resetting the toy project keeps repeated demos deterministic.
    reset_demo_project(mode="old")
    ensure_index()
    task = args.task
    console.print("[1/8] Parsing task\nTarget module: DRE")
    results = Retriever(provider_name=args.provider).search(task, top_k=5, module="DRE")
    console.print("[2/8] Retrieving historical experience")
    for idx, item in enumerate(results[:3], 1):
        console.print(f"#{idx} {item.chunk_id} score={item.score}")
    plan = _make_planner(args).plan(task, results)
    console.print("[3/8] Building execution plan")
    for step in plan["plan"]:
        console.print(f"- {step}")
    run_dir = new_run_dir("demo")
    _write_common_run_files(run_dir, task, results, plan)
    tools = ToolRegistry(run_dir)
    console.print("[4/8] Executing plan through controlled executor")
    execution = PlanExecutor(tools).execute(plan)
    write_json(run_dir / "execution.json", execution)
    console.print("[5/8] Running rollback validation")
    validation = execution.get("validation", {})
    rollback_status = _validate_rollback(tools) if execution["status"] == "success" else "not_run"
    validation["rollback"] = rollback_status
    _finalize(run_dir, task, _case_ids(results), validation, execution.get("modified_files", []))


def cmd_demo_failure(args: argparse.Namespace) -> None:
    """CLI command that demonstrates failure-triggered RAG recovery."""
    # The fixed teaching storyline lives in algo_rag_demo/demo_scenarios, away from reusable agent code.
    ensure_index()
    run_dre_failure_recovery_demo(
        provider_name=args.provider,
        planner=_make_planner(args),
        console=console,
    )


def _validate_rollback(tools: ToolRegistry) -> str:
    """Switch back to old_dre and verify rollback behavior."""
    # The config is returned to new_llf so the final state remains upgraded.
    tools.call("write_file", path="config/pipeline.json", content='{\n  "dre_algorithm": "old_dre"\n}\n')
    result = tools.call("verify_algorithm_switch", expected="old_dre")
    tools.call("write_file", path="config/pipeline.json", content='{\n  "dre_algorithm": "new_llf"\n}\n')
    return result["status"]


def _finalize(run_dir: Path, task: str, cases, validation: Dict[str, str], modified_files) -> None:
    """Write final report and print the demo result."""
    # Success requires every validation dimension to pass.
    write_json(run_dir / "validation.json", validation)
    status = "success" if all(value == "passed" for value in validation.values()) else "failed"
    report = {
        "status": status,
        "task": task,
        "retrieved_cases": cases,
        "modified_files": modified_files,
        "validation": validation,
    }
    write_json(run_dir / "final_report.json", report)
    console.print("[8/8] Final Result")
    console.print(status.upper())
    console.print(f"Run artifacts: {run_dir}")


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse command tree for all demo workflows."""
    # Subcommands mirror the README quick-start workflow.
    parser = argparse.ArgumentParser(description="Algorithm Upgrade RAG Agent Demo")
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("extract-case")
    p.add_argument("--extractor", default="rule", choices=["rule", "deepseek"])
    p.add_argument("--raw", help="Path to one raw conversation JSON file")
    p.add_argument("--output", help="Output case JSON path for one raw file")
    p.add_argument("--all", action="store_true", help="Extract every examples/data/raw/conversation_*.json file")
    p.add_argument("--base-url", default=None, help="DeepSeek OpenAI-compatible base URL")
    p.add_argument("--model", default=None, help="DeepSeek model name, for example deepseek-flash")
    p.set_defaults(func=cmd_extract_case)
    p = sub.add_parser("build-index")
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.set_defaults(func=cmd_build_index)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--module")
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("build-prompt")
    p.add_argument("task")
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.set_defaults(func=cmd_build_prompt)
    p = sub.add_parser("run-custom", help="run RAG retrieval and planning on caller-provided case data")
    p.add_argument("--task", help="Task text to retrieve and plan for")
    p.add_argument("--task-file", help="Path to a text file containing the task")
    p.add_argument("--case-dir", default=str(EXAMPLES_DIR / "custom_data" / "cases"))
    p.add_argument("--raw-dir", help="Optional raw conversation directory to extract into run-local cases")
    p.add_argument("--extractor", default="rule", choices=["rule", "deepseek"])
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.add_argument("--planner", default="evidence", choices=["evidence", "mock", "deepseek"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--module")
    p.add_argument("--skill-file", default=str(SKILL_FILE))
    p.add_argument("--repository-facts", help="Optional text file describing the target repository")
    p.add_argument("--base-url", default=None, help="DeepSeek OpenAI-compatible base URL")
    p.add_argument("--model", default=None, help="DeepSeek model name, for example deepseek-flash")
    p.set_defaults(func=cmd_run_custom)
    p = sub.add_parser("demo")
    p.add_argument("--task", required=True)
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.add_argument("--planner", default="mock", choices=["mock", "deepseek"])
    p.add_argument("--base-url", default=None, help="DeepSeek OpenAI-compatible base URL")
    p.add_argument("--model", default=None, help="DeepSeek model name, for example deepseek-flash")
    p.set_defaults(func=cmd_demo)
    p = sub.add_parser("demo-failure")
    p.add_argument("--provider", default="mock", choices=["mock", "bge-m3"])
    p.add_argument("--planner", default="mock", choices=["mock", "deepseek"])
    p.add_argument("--base-url", default=None, help="DeepSeek OpenAI-compatible base URL")
    p.add_argument("--model", default=None, help="DeepSeek model name, for example deepseek-flash")
    p.set_defaults(func=cmd_demo_failure)
    return parser


def main() -> None:
    """Parse CLI arguments and dispatch the selected subcommand."""
    # argparse stores the command handler in args.func.
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

