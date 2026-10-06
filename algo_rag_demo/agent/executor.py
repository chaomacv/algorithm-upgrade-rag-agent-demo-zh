from typing import Dict, List

from algo_rag_demo.agent.tool_registry import ToolRegistry


ADAPTER_FIXED = '''def run_dre(algorithm, image):
    result = algorithm.process(image)
    if "residual_map" not in result:
        result["residual_map"] = 0.0
    return result
'''

ADAPTER_BROKEN = '''def run_dre(algorithm, image):
    return algorithm.process(image)
'''

CONFIG_NEW = '''{
  "dre_algorithm": "new_llf"
}
'''

CONFIG_OLD = '''{
  "dre_algorithm": "old_dre"
}
'''


def apply_successful_change(tools: ToolRegistry) -> List[Dict[str, object]]:
    """Apply the adapter fix and switch the config to the new algorithm."""
    # The edit set mirrors the successful historical case.
    return [
        tools.call("write_file", path="src/modules/dre_adapter.py", content=ADAPTER_FIXED),
        tools.call("write_file", path="config/pipeline.json", content=CONFIG_NEW),
    ]


def apply_direct_replacement_failure(tools: ToolRegistry) -> List[Dict[str, object]]:
    """Apply the intentionally broken direct replacement attempt."""
    # This creates the missing residual_map failure used by demo-failure.
    return [
        tools.call("write_file", path="src/modules/dre_adapter.py", content=ADAPTER_BROKEN),
        tools.call("write_file", path="config/pipeline.json", content=CONFIG_NEW),
    ]


class PlanExecutor:
    """Execute a structured plan through the restricted ToolRegistry."""

    def __init__(self, tools: ToolRegistry, expected_algorithm: str = "new_llf") -> None:
        """Store execution dependencies for one demo run."""
        self.tools = tools
        self.expected_algorithm = expected_algorithm
        self.modified_files: List[str] = []

    def execute(self, plan: Dict[str, object], create_checkpoint: bool = True) -> Dict[str, object]:
        """Run executable plan steps and rollback on validation failure."""
        # The executor treats LLM output as intent and maps patches to safe templates.
        report: Dict[str, object] = {
            "status": "running",
            "steps": [],
            "validation": {},
            "modified_files": self.modified_files,
        }
        if create_checkpoint:
            report["checkpoint"] = self.tools.call("create_checkpoint")
        for step in self._steps_from_plan(plan):
            result = self._execute_step(step)
            report["steps"].append(result)
            if result.get("validation"):
                report["validation"] = result["validation"]
            if not result.get("ok", False):
                report["status"] = "failed"
                report["error"] = result.get("error", "step failed")
                report["rollback"] = self.tools.call("rollback")
                return report
        report["status"] = "success"
        report["modified_files"] = sorted(set(self.modified_files))
        return report

    def _steps_from_plan(self, plan: Dict[str, object]) -> List[Dict[str, object]]:
        """Read executable steps from a planner response."""
        executable = plan.get("executable_plan", {})
        steps = executable.get("steps", []) if isinstance(executable, dict) else []
        return [self._normalize_step(step) for step in steps]

    def _normalize_step(self, step: object) -> Dict[str, object]:
        """Convert loose planner output into a predictable step dictionary."""
        if isinstance(step, dict):
            return step
        text = str(step)
        lowered = text.lower()
        if "validate" in lowered or "test" in lowered:
            return {"type": "validate", "checks": ["build", "interface", "runtime", "algorithm_switch"]}
        if "search" in lowered:
            return {"type": "search", "query": "residual_map"}
        if "config" in lowered or "pipeline.json" in lowered:
            return {"type": "patch", "target": "demo_project/config/pipeline.json", "intent": "switch dre_algorithm to new_llf"}
        if "adapter" in lowered or "residual_map" in lowered:
            return {
                "type": "patch",
                "target": "demo_project/src/modules/dre_adapter.py",
                "intent": "preserve residual_map compatibility",
            }
        return {"type": "inspect", "target": "demo_project/src/modules/dre_adapter.py"}

    def _execute_step(self, step: Dict[str, object]) -> Dict[str, object]:
        """Dispatch one plan step to a safe tool or patch template."""
        step_type = str(step.get("type", step.get("action", "inspect"))).lower()
        if step_type in {"inspect", "read"}:
            target = self._tool_path(str(step.get("target", "demo_project/src/modules/dre_adapter.py")))
            if target.endswith("/") or target in {"tests", "tests/"}:
                return {
                    "ok": True,
                    "type": "inspect",
                    "target": target,
                    "tool_result": self.tools.call("search_code", query=""),
                }
            try:
                tool_result = self.tools.call("read_file", path=target)
            except IsADirectoryError:
                tool_result = self.tools.call("search_code", query="")
            return {"ok": True, "type": "inspect", "target": target, "tool_result": tool_result}
        if step_type == "search":
            query = str(step.get("query", step.get("target", "residual_map")))
            return {"ok": True, "type": "search", "query": query, "tool_result": self.tools.call("search_code", query=query)}
        if step_type in {"patch", "edit", "write"}:
            return self._apply_safe_patch(step)
        if step_type in {"backup", "checkpoint"}:
            return {
                "ok": True,
                "type": "backup",
                "note": "checkpoint already captured before executing the plan",
            }
        if step_type == "validate":
            checks = step.get("checks", ["build", "interface", "runtime", "algorithm_switch"])
            return self._run_checks(checks if isinstance(checks, list) else [str(checks)])
        return {"ok": False, "type": step_type, "error": f"unsupported step type: {step_type}"}

    def _apply_safe_patch(self, step: Dict[str, object]) -> Dict[str, object]:
        """Map patch intent to one of the demo's safe edit templates."""
        target = self._tool_path(str(step.get("target", "")))
        intent = str(step.get("intent", "")).lower()
        if "direct" in intent and ("without" in intent or "skip" in intent):
            result = self.tools.call("write_file", path="src/modules/dre_adapter.py", content=ADAPTER_BROKEN)
            self.modified_files.append("demo_project/src/modules/dre_adapter.py")
            return {"ok": result["ok"], "type": "patch", "target": "src/modules/dre_adapter.py", "tool_result": result}
        if "dre_adapter.py" in target or "residual_map" in intent or "adapter" in intent:
            result = self.tools.call("write_file", path="src/modules/dre_adapter.py", content=ADAPTER_FIXED)
            self.modified_files.append("demo_project/src/modules/dre_adapter.py")
            return {"ok": result["ok"], "type": "patch", "target": "src/modules/dre_adapter.py", "tool_result": result}
        if "pipeline.json" in target or "new_llf" in intent or "algorithm" in intent:
            result = self.tools.call("write_file", path="config/pipeline.json", content=CONFIG_NEW)
            self.modified_files.append("demo_project/config/pipeline.json")
            return {"ok": result["ok"], "type": "patch", "target": "config/pipeline.json", "tool_result": result}
        return {"ok": False, "type": "patch", "target": target, "error": "patch target or intent is not allowed"}

    def _run_checks(self, checks: List[object]) -> Dict[str, object]:
        """Run requested validations and fail fast on the first failed check."""
        validation: Dict[str, str] = {}
        for raw_check in checks:
            check = str(raw_check).lower()
            if check == "build":
                result = self.tools.call("run_build_check")
            elif "interface" in check or "residual_map" in check:
                result = self.tools.call("run_interface_tests")
                check = "interface" if check == "interface" else check
            elif check == "runtime":
                result = self.tools.call("run_runtime_tests")
            elif check in {"algorithm_switch", "switch"}:
                result = self.tools.call("verify_algorithm_switch", expected=self.expected_algorithm)
                check = "algorithm_switch"
            elif "test" in check or "regression" in check:
                result = self._run_unit_test_bundle()
            elif "rollback" in check:
                result = {"ok": True, "status": "passed" if self.tools.checkpoint_dir.exists() else "failed"}
            else:
                result = {"ok": False, "status": "failed", "error": f"unknown validation check: {check}"}
            validation[check] = result["status"]
            if not result.get("ok", False):
                return {
                    "ok": False,
                    "type": "validate",
                    "validation": validation,
                    "error": result.get("error", f"{check} failed"),
                }
        return {"ok": True, "type": "validate", "validation": validation}

    def _run_unit_test_bundle(self) -> Dict[str, object]:
        """Run the demo's closest equivalent to focused unit/regression tests."""
        # The toy project exposes validations through ToolRegistry rather than pytest.
        checks = [
            self.tools.call("run_interface_tests"),
            self.tools.call("run_runtime_tests"),
            self.tools.call("verify_algorithm_switch", expected=self.expected_algorithm),
        ]
        ok = all(item.get("ok", False) for item in checks)
        return {"ok": ok, "status": "passed" if ok else "failed", "details": checks}

    def _tool_path(self, path: str) -> str:
        """Convert demo_project-prefixed paths into ToolRegistry-relative paths."""
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized.startswith("demo_project/"):
            normalized = normalized[len("demo_project/"):]
        return normalized

