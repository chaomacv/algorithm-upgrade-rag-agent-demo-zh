from algo_rag_demo.agent.executor import PlanExecutor
from algo_rag_demo.agent.tool_registry import ToolRegistry, new_run_dir
from algo_rag_demo.scaffold import reset_demo_project


def test_plan_executor_runs_safe_repair_plan():
    """Verify PlanExecutor applies safe patches and validates the upgrade."""
    reset_demo_project(mode="old")
    tools = ToolRegistry(new_run_dir("pytest-plan-executor"))
    plan = {
        "executable_plan": {
            "steps": [
                {"type": "inspect", "target": "demo_project/src/modules/dre_adapter.py"},
                {
                    "type": "patch",
                    "target": "demo_project/src/modules/dre_adapter.py",
                    "intent": "preserve residual_map compatibility",
                },
                {
                    "type": "patch",
                    "target": "demo_project/config/pipeline.json",
                    "intent": "switch dre_algorithm to new_llf",
                },
                {"type": "validate", "checks": ["build", "interface", "runtime", "algorithm_switch"]},
            ]
        }
    }

    report = PlanExecutor(tools).execute(plan)

    assert report["status"] == "success"
    assert report["validation"]["interface"] == "passed"
    assert "demo_project/src/modules/dre_adapter.py" in report["modified_files"]


def test_plan_executor_rolls_back_failed_direct_replacement():
    """Verify PlanExecutor rolls back when direct replacement breaks interface."""
    reset_demo_project(mode="old")
    tools = ToolRegistry(new_run_dir("pytest-plan-failure"))
    plan = {
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
                {"type": "validate", "checks": ["interface"]},
            ]
        }
    }

    report = PlanExecutor(tools).execute(plan)

    assert report["status"] == "failed"
    assert "residual_map" in report["error"]
    assert tools.call("verify_algorithm_switch", expected="old_dre")["status"] == "passed"
