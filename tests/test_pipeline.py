from algo_rag_demo.agent.executor import apply_successful_change
from algo_rag_demo.agent.tool_registry import ToolRegistry, new_run_dir
from algo_rag_demo.scaffold import reset_demo_project


def test_full_pipeline_validation():
    """Verify the full mock agent workflow passes all validations."""
    # The toy project is reset so previous demo runs cannot affect the test.
    reset_demo_project(mode="old")
    tools = ToolRegistry(new_run_dir("pytest"))
    tools.call("create_checkpoint")
    apply_successful_change(tools)
    assert tools.call("run_interface_tests")["status"] == "passed"
    assert tools.call("run_build_check")["status"] == "passed"
    assert tools.call("run_runtime_tests")["status"] == "passed"
    assert tools.call("verify_algorithm_switch", expected="new_llf")["status"] == "passed"
    tools.call("write_file", path="config/pipeline.json", content='{\n  "dre_algorithm": "old_dre"\n}\n')
    assert tools.call("verify_algorithm_switch", expected="old_dre")["status"] == "passed"

