import argparse
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table

from algo_rag_demo.agent.llm_provider import build_chat_provider
from algo_rag_demo.agent.planner import LLMPlanner
from algo_rag_demo.agent.executor import build_project_adapter
from algo_rag_demo.agent.workflow import run_agent
from algo_rag_demo.case_pipeline.parser import LLMCaseExtractor, extract_case_directory
from algo_rag_demo.config import CASE_DIR, DEFAULT_CONFIG, INDEX_DIR, KNOWLEDGE_DIR, RUNS_DIR
from algo_rag_demo.rag.index_builder import build_index_from_cases
from algo_rag_demo.rag.prompt_builder import build_prompt
from algo_rag_demo.rag.retriever import Retriever
from algo_rag_demo.utils.jsonio import read_json, write_json

console = Console()


def _load_config(path: str = None) -> Dict[str, object]:
    """Load JSON config and apply small defaults."""
    config_path = Path(path) if path else DEFAULT_CONFIG
    config = read_json(config_path)
    config.setdefault("llm", {})
    config.setdefault("embedding", {})
    config.setdefault("retrieval", {})
    config.setdefault("paths", {})
    return config


def _path(value: str, default: Path) -> Path:
    """Resolve a user path or fallback path."""
    return Path(value) if value else default


def _task_text(args: argparse.Namespace) -> str:
    """Load task text from --task or --task-file."""
    if args.task:
        return args.task
    if args.task_file:
        return Path(args.task_file).read_text(encoding="utf-8").strip()
    raise ValueError("Either --task or --task-file is required.")


def _run_dir(prefix: str = "run") -> Path:
    """Create one timestamped output directory."""
    import time

    import uuid
    path = RUNS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{prefix}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _llm_planner(config: Dict[str, object]):
    """Create the configured planner."""
    return LLMPlanner(build_chat_provider(config.get("llm", {})))


def _embedding_settings(config: Dict[str, object]) -> Dict[str, str]:
    """Return embedding provider name and model from config."""
    embedding = config.get("embedding", {})
    return {
        "provider": str(embedding.get("provider", "bge-m3")),
        "model": embedding.get("model") if isinstance(embedding.get("model"), str) else None,
    }


def _case_ids(results) -> List[str]:
    """Return unique case ids from retrieval results."""
    return list(dict.fromkeys(item.case_id for item in results))


def cmd_extract_cases(args: argparse.Namespace) -> None:
    """Extract structured cases from a directory of historical conversations."""
    config = _load_config(args.config)
    provider = build_chat_provider(config.get("llm", {}))
    extractor = LLMCaseExtractor(provider)
    raw_dir = Path(args.raw_dir)
    case_dir = Path(args.case_dir)
    for case, final_path in extract_case_directory(raw_dir, case_dir, extractor):
        console.print(f"Extracted {case.case_id} -> {final_path}")


def cmd_build_index(args: argparse.Namespace) -> None:
    """Build chunks, embeddings, and a vector index from structured cases."""
    config = _load_config(args.config)
    embedding = _embedding_settings(config)
    cases, chunks, dimension = build_index_from_cases(
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=Path(args.case_dir),
        knowledge_dir=Path(args.knowledge_dir),
        index_dir=Path(args.index_dir),
    )
    console.print(f"Loaded {cases} cases")
    console.print(f"Generated {chunks} chunks")
    console.print(f"Embedding dimension: {dimension}")
    console.print(f"Saved index to {args.index_dir}")


def cmd_search(args: argparse.Namespace) -> None:
    """Retrieve top-k chunks for one task or query."""
    config = _load_config(args.config)
    embedding = _embedding_settings(config)
    query = _task_text(args)
    top_k = args.top_k or int(config.get("retrieval", {}).get("top_k", 5))
    results = Retriever(
        index_dir=Path(args.index_dir),
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=Path(args.case_dir),
    ).search(query, top_k=top_k, module=args.module)
    table = Table(title="Retrieval Results")
    table.add_column("Rank")
    table.add_column("Case")
    table.add_column("Chunk")
    table.add_column("Score")
    table.add_column("Text")
    for idx, item in enumerate(results, 1):
        table.add_row(str(idx), item.case_id, item.chunk_type, f"{item.score:.4f}", item.text[:120])
    console.print(table)


def cmd_plan(args: argparse.Namespace) -> None:
    """Generate a plan from an existing index and structured cases."""
    config = _load_config(args.config)
    embedding = _embedding_settings(config)
    task = _task_text(args)
    top_k = args.top_k or int(config.get("retrieval", {}).get("top_k", 5))
    repository_facts = Path(args.repository_facts).read_text(encoding="utf-8") if args.repository_facts else ""
    results = Retriever(
        index_dir=Path(args.index_dir),
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=Path(args.case_dir),
    ).search(task, top_k=top_k, module=args.module)
    plan = _llm_planner(config).plan(task, results, repository_facts)
    run_dir = _run_dir("plan")
    _write_run_artifacts(run_dir, task, results, plan, repository_facts)
    console.print(f"Plan artifacts: {run_dir}")


def cmd_run(args: argparse.Namespace) -> None:
    """Ensure preparation failures also produce an auditable final report."""
    config = _load_config(args.config)
    run_dir = _run_dir("algorithm-upgrade")
    try:
        _run_pipeline(args, config, run_dir)
    except (Exception, KeyboardInterrupt) as exc:
        report_path = run_dir / "final_report.json"
        if not report_path.exists():
            write_json(report_path, {"status": "failed", "error": str(exc) or type(exc).__name__,
                                    "attempts": [], "rollback": None})
        console.print(f"Run artifacts: {run_dir}")
        raise


def _run_pipeline(args: argparse.Namespace, config: Dict[str, object], run_dir: Path) -> None:
    """Run case extraction, RAG planning, project execution, validation, and recovery."""
    paths = config.get("paths", {})
    case_dir = _path(args.case_dir, Path(paths.get("case_dir", CASE_DIR)))
    default_cases = Path(paths.get("case_dir", CASE_DIR))
    raw_value = args.raw_dir or (paths.get("raw_dir") if case_dir.resolve() == default_cases.resolve() else None)
    raw_dir = Path(raw_value) if raw_value else None
    execution = config.get("execution")
    if not args.plan_only:
        if not execution:
            raise ValueError("Configure execution.factory and project checks, or use --plan-only.")
        if (case_dir.resolve() != CASE_DIR.resolve() or
                (raw_dir and raw_dir.resolve() != (CASE_DIR.parent / "raw").resolve())) and execution.get("demo_only"):
            raise ValueError("Custom data needs its own execution config; see docs/execution_validation.md.")
    if not args.task and not args.task_file:
        args.task_file = paths.get("task_file")
    task = _task_text(args)
    if not task.strip():
        raise ValueError("Task text must not be empty.")
    facts_path = args.repository_facts or paths.get("repository_facts")
    repository_facts = Path(facts_path).read_text(encoding="utf-8") if facts_path else ""
    provider = build_chat_provider(config.get("llm", {}))
    planner = LLMPlanner(provider)
    write_json(run_dir / "task.json", {"task": task})
    working_case_dir = run_dir / "cases" if raw_dir else case_dir
    if raw_dir:
        import shutil
        shutil.copytree(raw_dir, run_dir / "conversations")
        for case, output in extract_case_directory(raw_dir, working_case_dir, LLMCaseExtractor(provider)):
            console.print(f"Extracted {case.case_id} -> {output}")
    embedding = _embedding_settings(config)
    index_dir = run_dir / "index"
    knowledge_dir = run_dir / "knowledge"
    cases, chunks, dimension = build_index_from_cases(
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=working_case_dir,
        knowledge_dir=knowledge_dir,
        index_dir=index_dir,
    )
    top_k = args.top_k or int(config.get("retrieval", {}).get("top_k", 5))
    retriever = Retriever(
        index_dir=index_dir,
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=working_case_dir,
    )
    if args.plan_only:
        results = retriever.search(task, top_k=top_k, module=args.module)
        plan = planner.plan(task, results, repository_facts)
        _write_run_artifacts(run_dir, task, results, plan, repository_facts)
        report = {"status": "planned"}
    else:
        adapter = build_project_adapter(execution, run_dir)
        skill_path = execution.get("skill_file")
        skill = Path(skill_path).read_text(encoding="utf-8") if skill_path else ""
        report = run_agent(
            task, retriever, planner, adapter, run_dir, repository_facts, skill,
            top_k=top_k, module=args.module,
            max_attempts=int(execution.get("max_attempts", 3)),
        )
        report.update({"cases_loaded": cases, "chunks_generated": chunks,
                       "embedding_dimension": dimension, "case_dir": str(working_case_dir),
                       "index_dir": str(index_dir), "knowledge_dir": str(knowledge_dir)})
        write_json(run_dir / "final_report.json", report)
    console.print(f"Cases: {cases}, chunks: {chunks}, dimension: {dimension}")
    console.print(f"Status: {report['status']}")
    console.print(f"Run artifacts: {run_dir}")
    if report["status"] not in {"success", "planned"}:
        raise SystemExit(1)


def _write_run_artifacts(
    run_dir: Path,
    task: str,
    results,
    plan: Dict[str, object],
    repository_facts: str,
) -> None:
    """Write auditable output files for one pipeline run."""
    write_json(run_dir / "task.json", {"task": task})
    write_json(run_dir / "retrieval.json", [item.model_dump() for item in results])
    write_json(run_dir / "plan.json", plan)
    prompt = build_prompt(task, results, repository_facts)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    report = {
        "status": "planned",
        "retrieved_cases": _case_ids(results),
        "note": "Plan-only mode: project execution and validation were not run.",
    }
    write_json(run_dir / "final_report.json", report)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse command tree for the generic RAG planning pipeline."""
    parser = argparse.ArgumentParser(description="Configurable RAG planning pipeline")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="JSON config path")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("extract-cases")
    p.add_argument("--raw-dir", required=True)
    p.add_argument("--case-dir", required=True)
    p.set_defaults(func=cmd_extract_cases)

    p = sub.add_parser("build-index")
    p.add_argument("--case-dir", default=str(CASE_DIR))
    p.add_argument("--knowledge-dir", default=str(KNOWLEDGE_DIR))
    p.add_argument("--index-dir", default=str(INDEX_DIR))
    p.add_argument("--embedding-provider")
    p.add_argument("--embedding-model")
    p.set_defaults(func=cmd_build_index)

    p = sub.add_parser("search")
    p.add_argument("--task")
    p.add_argument("--task-file")
    p.add_argument("--case-dir", default=str(CASE_DIR))
    p.add_argument("--index-dir", default=str(INDEX_DIR))
    p.add_argument("--embedding-provider")
    p.add_argument("--embedding-model")
    p.add_argument("--top-k", type=int)
    p.add_argument("--module")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("plan")
    p.add_argument("--task")
    p.add_argument("--task-file")
    p.add_argument("--case-dir", default=str(CASE_DIR))
    p.add_argument("--index-dir", default=str(INDEX_DIR))
    p.add_argument("--repository-facts")
    p.add_argument("--embedding-provider")
    p.add_argument("--embedding-model")
    p.add_argument("--top-k", type=int)
    p.add_argument("--module")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("run")
    p.add_argument("--raw-dir", help="Optional historical conversation directory to extract first")
    p.add_argument("--case-dir", help="Structured CASE_*.json directory")
    p.add_argument("--task")
    p.add_argument("--task-file")
    p.add_argument("--repository-facts")
    p.add_argument("--embedding-provider")
    p.add_argument("--embedding-model")
    p.add_argument("--top-k", type=int)
    p.add_argument("--module")
    p.add_argument("--plan-only", action="store_true", help="Generate a plan without executing project tools")
    p.set_defaults(func=cmd_run)
    return parser


def main() -> None:
    """Parse CLI arguments and dispatch the selected command."""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
