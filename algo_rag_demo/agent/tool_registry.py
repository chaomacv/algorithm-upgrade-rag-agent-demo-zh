import compileall
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

from algo_rag_demo.config import DEMO_PROJECT_DIR, RUNS_DIR
from algo_rag_demo.utils.jsonio import write_json


class ToolRegistry:
    """Small fixed tool registry with path and command restrictions."""

    def __init__(self, run_dir: Path) -> None:
        """Prepare logging and checkpoint paths for one agent run."""
        self.run_dir = run_dir
        self.tool_log = run_dir / "tool_calls.jsonl"
        self.checkpoint_dir = run_dir / "checkpoint"
        run_dir.mkdir(parents=True, exist_ok=True)

    def call(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute one whitelisted tool and append a structured log row."""
        # Tool names are explicit to avoid arbitrary shell execution.
        tools = {
            "read_file": self.read_file,
            "search_code": self.search_code,
            "write_file": self.write_file,
            "run_interface_tests": self.run_interface_tests,
            "run_build_check": self.run_build_check,
            "run_runtime_tests": self.run_runtime_tests,
            "verify_algorithm_switch": self.verify_algorithm_switch,
            "create_checkpoint": self.create_checkpoint,
            "rollback": self.rollback,
        }
        if name not in tools:
            raise ValueError(f"Unsupported tool: {name}")
        started = time.time()
        result = tools[name](**kwargs)
        entry = {"tool": name, "args": kwargs, "result": result, "elapsed_ms": int((time.time() - started) * 1000)}
        with self.tool_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return result

    def _safe_path(self, relative_path: str) -> Path:
        """Resolve a path and reject access outside demo_project."""
        # All file tools are sandboxed to the toy project.
        path = (DEMO_PROJECT_DIR / relative_path).resolve()
        root = DEMO_PROJECT_DIR.resolve()
        if root not in path.parents and path != root:
            raise ValueError("Tool path escapes demo_project")
        return path

    def read_file(self, path: str) -> Dict[str, Any]:
        """Read one safe demo_project file."""
        # Return structured data so the caller can log tool output.
        target = self._safe_path(path)
        return {"ok": True, "content": target.read_text(encoding="utf-8")}

    def search_code(self, query: str) -> Dict[str, Any]:
        """Find Python files inside demo_project containing a query string."""
        # This is a fixed safe search, not a general shell grep.
        matches: List[str] = []
        for path in DEMO_PROJECT_DIR.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if query in text:
                matches.append(str(path.relative_to(DEMO_PROJECT_DIR)))
        return {"ok": True, "matches": matches}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write one safe demo_project file."""
        # Parent directories are allowed only under demo_project.
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(target.relative_to(DEMO_PROJECT_DIR))}

    def create_checkpoint(self) -> Dict[str, Any]:
        """Copy demo_project into the run checkpoint directory."""
        # The checkpoint gives rollback a known-good project state.
        if self.checkpoint_dir.exists():
            shutil.rmtree(str(self.checkpoint_dir))
        shutil.copytree(str(DEMO_PROJECT_DIR), str(self.checkpoint_dir))
        return {"ok": True, "checkpoint": str(self.checkpoint_dir)}

    def rollback(self) -> Dict[str, Any]:
        """Restore demo_project from the saved checkpoint."""
        # Rollback is intentionally file-copy based for transparency.
        if not self.checkpoint_dir.exists():
            return {"ok": False, "error": "checkpoint missing"}
        if DEMO_PROJECT_DIR.exists():
            shutil.rmtree(str(DEMO_PROJECT_DIR))
        shutil.copytree(str(self.checkpoint_dir), str(DEMO_PROJECT_DIR))
        return {"ok": True}

    def run_build_check(self) -> Dict[str, Any]:
        """Compile Python sources as the demo build check."""
        # compileall catches syntax/import-time bytecode problems cheaply.
        ok = compileall.compile_dir(str(DEMO_PROJECT_DIR / "src"), quiet=1)
        return {"ok": bool(ok), "status": "passed" if ok else "failed"}

    def run_interface_tests(self) -> Dict[str, Any]:
        """Verify runtime output contains the required public fields."""
        # The interface check catches NewLLF missing residual_map.
        try:
            result = _run_pipeline()
            missing = [key for key in ["image", "residual_map", "metadata"] if key not in result]
            if missing:
                return {"ok": False, "status": "failed", "error": f"missing field: {missing[0]}"}
            return {"ok": True, "status": "passed"}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def run_runtime_tests(self) -> Dict[str, Any]:
        """Run the full toy pipeline and report the active algorithm."""
        # Runtime evidence is stronger than a build-only success.
        try:
            result = _run_pipeline()
            return {"ok": True, "status": "passed", "algorithm": result["metadata"]["algorithm"]}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def verify_algorithm_switch(self, expected: str = "new_llf") -> Dict[str, Any]:
        """Check that runtime metadata reports the expected algorithm."""
        # This prevents declaring success while config still selects old_dre.
        try:
            result = _run_pipeline()
            actual = result["metadata"]["algorithm"]
            return {"ok": actual == expected, "status": "passed" if actual == expected else "failed", "actual": actual}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}


def _run_pipeline() -> Dict[str, Any]:
    """Import and execute the current demo pipeline implementation."""
    # Drop cached modules so file edits are reflected immediately.
    import sys

    src_path = str((DEMO_PROJECT_DIR / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    for module in ["main", "pipeline", "modules.dre_adapter"]:
        if module in sys.modules:
            del sys.modules[module]
    import importlib

    main = importlib.import_module("main")
    return main.run()


def new_run_dir(prefix: str) -> Path:
    """Create a timestamped run directory for logs and reports."""
    # Prefix names keep different demo modes easy to identify.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = RUNS_DIR / f"{stamp}-{prefix}"
    path.mkdir(parents=True, exist_ok=True)
    return path

