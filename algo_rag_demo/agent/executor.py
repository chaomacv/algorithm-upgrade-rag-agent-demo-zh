import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Protocol


class ProjectAdapter(Protocol):
    """Contract for project-specific execution, validation, and rollback."""

    def facts(self) -> str:
        """Return current files and tool constraints for the planner."""
        ...

    def checkpoint(self) -> None:
        """Capture the pre-change state."""
        ...

    def execute(self, plan: Dict[str, object]) -> Dict[str, object]:
        """Apply structured actions using the project's restricted tools."""
        ...

    def validate(self) -> Dict[str, object]:
        """Run project checks and return passed, checks, and error details."""
        ...

    def rollback(self) -> Dict[str, object]:
        """Restore the checkpoint and verify restoration."""
        ...


class FileProjectAdapter:
    """Apply allowlisted file edits in a run-local copy and run configured checks."""

    def __init__(self, config: Dict[str, object], run_dir: Path) -> None:
        """Copy the configured project and load its explicit execution boundary."""
        self.workspace = (run_dir / "workspace").resolve()
        self.checkpoint_dir = run_dir / "checkpoint"
        shutil.copytree(
            Path(config["template_dir"]), self.workspace,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "outputs", "runs"),
        )
        self.allowed_files = list(config["allowed_files"])
        self.commands = config["validation_commands"]
        self.timeout = int(config.get("timeout", 60))
        self.original = {}
        # Resolve all edit paths before either checkpointing or mutation.
        for name in self.allowed_files:
            self._path(name)

    def _path(self, name: str) -> Path:
        """Resolve an allowlisted relative path inside the copied workspace."""
        if name not in self.allowed_files or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"File is not allowlisted: {name}")
        path = (self.workspace / name).resolve()
        path.relative_to(self.workspace.resolve())
        return path

    def facts(self) -> str:
        """Expose editable file contents and the fixed validation contract."""
        files = {
            name: self._path(name).read_text(encoding="utf-8")
            if self._path(name).exists() else None
            for name in self.allowed_files
        }
        import json
        return json.dumps({
            "workspace": str(self.workspace),
            "editable_files": files,
            "available_tools": ["write_file"],
            "action_schema": {"tool": "write_file", "path": "allowlisted path", "content": "complete file text"},
            "validation_commands": self.commands,
            "instruction": "Return actions with complete file contents. Do not edit validation tests.",
        }, ensure_ascii=False, indent=2)

    def checkpoint(self) -> None:
        """Save the exact original bytes of every editable file."""
        self.original = {
            name: self._path(name).read_bytes() if self._path(name).exists() else None
            for name in self.allowed_files
        }
        from algo_rag_demo.utils.jsonio import write_json
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        write_json(self.checkpoint_dir / "manifest.json", {
            name: {"existed": content is not None} for name, content in self.original.items()
        })
        for name, content in self.original.items():
            if content is not None:
                snapshot = self.checkpoint_dir / name
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_bytes(content)

    def execute(self, plan: Dict[str, object]) -> Dict[str, object]:
        """Validate the entire action batch before writing any allowed file."""
        actions = plan.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError("Planner must return a non-empty actions list.")
        pending = []
        for action in actions:
            if not isinstance(action, dict) or action.get("tool") != "write_file":
                raise ValueError("Only the write_file tool is available.")
            content = action.get("content")
            if not isinstance(content, str):
                raise ValueError("write_file.content must be a string.")
            pending.append((self._path(action.get("path", "")), content))
        for path, content in pending:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return {"applied": True, "files": [str(path.relative_to(self.workspace)) for path, _ in pending]}

    def validate(self) -> Dict[str, object]:
        """Run every fixed validation command and preserve actual process output."""
        checks = []
        if not self.commands:
            raise ValueError("At least one validation command is required.")
        for command in self.commands:
            if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
                raise ValueError("Validation commands must be non-empty argv lists.")
            argv = [sys.executable if value == "{python}" else value for value in command]
            try:
                process = subprocess.run(
                    argv, cwd=self.workspace, capture_output=True, text=True,
                    timeout=self.timeout, shell=False,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                )
                checks.append({
                    "command": command, "passed": process.returncode == 0,
                    "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
                })
            except subprocess.TimeoutExpired:
                checks.append({"command": command, "passed": False, "error": "Validation timed out."})
        return {"passed": all(check["passed"] for check in checks), "checks": checks}

    def rollback(self) -> Dict[str, object]:
        """Restore original file bytes and verify the complete checkpoint."""
        for name, content in self.original.items():
            path = self._path(name)
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        restored = all(
            (self._path(name).read_bytes() if self._path(name).exists() else None) == content
            for name, content in self.original.items()
        )
        return {"restored": restored, "files": list(self.original)}


def build_project_adapter(config: Dict[str, object], run_dir: Path) -> ProjectAdapter:
    """Load the configured adapter factory without depending on one project domain."""
    module_name, factory_name = str(config.get(
        "factory", "algo_rag_demo.agent.executor:FileProjectAdapter"
    )).split(":", 1)
    factory = getattr(importlib.import_module(module_name), factory_name)
    return factory(config, run_dir)
