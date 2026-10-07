import argparse
from pathlib import Path
from typing import Dict, List

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover
    class Console:
        def print(self, value="") -> None:
            print(value)

    class Table:
        def __init__(self, title: str = "") -> None:
            self.title = title
            self.columns = []
            self.rows = []

        def add_column(self, name: str) -> None:
            self.columns.append(name)

        def add_row(self, *values: str) -> None:
            self.rows.append(values)

        def __str__(self) -> str:
            lines = [self.title] if self.title else []
            if self.columns:
                lines.append(" | ".join(self.columns))
                lines.append("-" * max(20, len(lines[-1])))
            lines.extend(" | ".join(row) for row in self.rows)
            return "\n".join(lines)

from algo_rag_demo.agent.llm_provider import build_chat_provider
from algo_rag_demo.agent.planner import EvidencePlanner, LLMPlanner
from algo_rag_demo.case_pipeline.parser import LLMCaseExtractor, extract_case_file
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

    path = RUNS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{prefix}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _llm_planner(config: Dict[str, object], offline: bool = False):
    """Create the configured planner."""
    if offline:
        return EvidencePlanner()
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
    raw_paths = sorted(raw_dir.glob("*.json"))
    if not raw_paths:
        raise ValueError(f"No raw conversation JSON files found in {raw_dir}")
    case_dir.mkdir(parents=True, exist_ok=True)
    for raw_path in raw_paths:
        temp_path = case_dir / f"{raw_path.stem}.json"
        case = extract_case_file(raw_path, temp_path, extractor)
        final_path = case_dir / f"{case.case_id}.json"
        if temp_path != final_path:
            temp_path.unlink(missing_ok=True)
        write_json(final_path, case)
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
        table.add_row(str(idx), item.case_id, item.chunk_type, str(item.score), item.text[:120])
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
    plan = _llm_planner(config, offline=args.offline).plan(task, results, repository_facts)
    run_dir = _run_dir("plan")
    _write_run_artifacts(run_dir, task, results, plan, repository_facts)
    console.print(f"Plan artifacts: {run_dir}")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the complete case-to-index-to-retrieval-to-plan pipeline."""
    config = _load_config(args.config)
    paths = config.get("paths", {})
    case_dir = _path(args.case_dir, Path(paths.get("case_dir", CASE_DIR)))
    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    run_dir = _run_dir("rag-plan")
    working_case_dir = run_dir / "cases" if raw_dir else case_dir
    if raw_dir:
        args_for_extract = argparse.Namespace(
            config=args.config,
            raw_dir=str(raw_dir),
            case_dir=str(working_case_dir),
        )
        cmd_extract_cases(args_for_extract)
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
    task = _task_text(args)
    repository_facts = Path(args.repository_facts).read_text(encoding="utf-8") if args.repository_facts else ""
    top_k = args.top_k or int(config.get("retrieval", {}).get("top_k", 5))
    results = Retriever(
        index_dir=index_dir,
        provider_name=args.embedding_provider or embedding["provider"],
        embedding_model=args.embedding_model or embedding["model"],
        case_dir=working_case_dir,
    ).search(task, top_k=top_k, module=args.module)
    plan = _llm_planner(config, offline=args.offline).plan(task, results, repository_facts)
    _write_run_artifacts(
        run_dir,
        task,
        results,
        plan,
        repository_facts,
        extra={
            "cases_loaded": cases,
            "chunks_generated": chunks,
            "embedding_dimension": dimension,
            "case_dir": str(working_case_dir),
            "index_dir": str(index_dir),
            "knowledge_dir": str(knowledge_dir),
        },
    )
    console.print(f"Cases: {cases}, chunks: {chunks}, dimension: {dimension}")
    for idx, item in enumerate(results, 1):
        console.print(f"#{idx} {item.chunk_id} score={item.score}")
    console.print(f"Run artifacts: {run_dir}")


def _write_run_artifacts(
    run_dir: Path,
    task: str,
    results,
    plan: Dict[str, object],
    repository_facts: str,
    extra: Dict[str, object] = None,
) -> None:
    """Write auditable output files for one pipeline run."""
    write_json(run_dir / "task.json", {"task": task})
    write_json(run_dir / "retrieval.json", [item.dict() if hasattr(item, "dict") else item for item in results])
    write_json(run_dir / "plan.json", plan)
    prompt = build_prompt(task, results, repository_facts)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    report = {
        "status": "planned",
        "retrieved_cases": _case_ids(results),
        "note": "This pipeline produces a RAG-backed plan. Execution is intentionally left to a project-specific tool layer.",
    }
    if extra:
        report.update(extra)
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
    p.add_argument("--offline", action="store_true", help="Use deterministic EvidencePlanner instead of LLM")
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
    p.add_argument("--offline", action="store_true", help="Use deterministic EvidencePlanner instead of LLM")
    p.set_defaults(func=cmd_run)
    return parser


def main() -> None:
    """Parse CLI arguments and dispatch the selected command."""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
