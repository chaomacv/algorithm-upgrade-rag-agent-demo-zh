from pathlib import Path

from algo_rag_demo.config import DEMO_PROJECT_DIR


FILES = {
    "README.md": """# Demo Algorithm Project

This toy project simulates a modular algorithm pipeline with a replaceable DRE module. It is
synthetic and exists only to demonstrate interface adaptation, validation, and
rollback in a Coding Agent workflow.
""",
    "config/pipeline.json": '{\n  "dre_algorithm": "old_dre"\n}\n',
    "src/algorithms/old_dre.py": '''class OldDRE:
    name = "old_dre"

    def process(self, image):
        """Return the legacy DRE output schema with residual_map."""
        # Downstream code depends on all three returned fields.
        return {
            "image": image * 1.0,
            "residual_map": 0.1,
            "metadata": {
                "algorithm": self.name
            }
        }
''',
    "src/algorithms/new_llf.py": '''class NewLLF:
    name = "new_llf"

    def process(self, image):
        """Return the new algorithm output that lacks residual_map."""
        # The missing field is deliberate so the adapter fix is necessary.
        return {
            "image": image * 1.1,
            "metadata": {
                "algorithm": self.name
            }
        }
''',
    "src/modules/dre_adapter.py": '''def run_dre(algorithm, image):
    """Run the selected DRE algorithm through the adapter boundary."""
    # The initial version is intentionally too thin for the failure demo.
    return algorithm.process(image)
''',
    "src/pipeline.py": '''import json
from pathlib import Path

from algorithms.new_llf import NewLLF
from algorithms.old_dre import OldDRE
from modules.dre_adapter import run_dre


class ColorTransform:
    def process(self, dre_result):
        """Apply a tiny downstream transform that requires residual_map."""
        # This dependency makes adapter compatibility observable in tests.
        residual = dre_result["residual_map"]
        return {
            "image": dre_result["image"] + residual,
            "residual_map": residual,
            "metadata": dre_result["metadata"],
        }


class Pipeline:
    def __init__(self, config_path=None):
        """Initialize the pipeline with a configurable pipeline.json path."""
        # Tests can pass a custom config, while the demo uses the default file.
        root = Path(__file__).resolve().parents[1]
        self.config_path = Path(config_path) if config_path else root / "config" / "pipeline.json"

    def _load_algorithm(self):
        """Instantiate the DRE algorithm selected by configuration."""
        # The algorithm switch validation checks this config-driven choice.
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        name = config["dre_algorithm"]
        if name == "old_dre":
            return OldDRE()
        if name == "new_llf":
            return NewLLF()
        raise ValueError(f"Unknown DRE algorithm: {name}")

    def run(self, image=1.0):
        """Run DRE through the adapter and downstream color transform."""
        # The adapter is where old/new algorithm interface compatibility lives.
        algorithm = self._load_algorithm()
        dre_result = run_dre(algorithm, image)
        return ColorTransform().process(dre_result)
''',
    "src/main.py": '''from pipeline import Pipeline


def run():
    """Run the toy algorithm pipeline with its default configuration."""
    # The CLI and tests use this function as the runtime entry point.
    return Pipeline().run(image=1.0)


if __name__ == "__main__":
    print(run())
''',
    "tests/test_interface.py": '''from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_interface_contains_required_fields():
    """Verify the pipeline output keeps the required public fields."""
    # Missing residual_map is the expected failure for a direct replacement.
    result = run()
    assert "image" in result
    assert "residual_map" in result
    assert "metadata" in result
''',
    "tests/test_runtime.py": '''from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_runtime_completes():
    """Verify the toy pipeline runs without exceptions."""
    # A positive image value is enough for this synthetic runtime check.
    assert run()["image"] > 0
''',
    "tests/test_algorithm_switch.py": '''import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_algorithm_switch_to_new_llf():
    """Verify config can activate NewLLF when the adapter is compatible."""
    # Patch the adapter inside the test so the initial demo can remain broken.
    config = ROOT / "config" / "pipeline.json"
    adapter = ROOT / "src" / "modules" / "dre_adapter.py"
    original_config = config.read_text(encoding="utf-8")
    original_adapter = adapter.read_text(encoding="utf-8")
    try:
        adapter.write_text(
            'def run_dre(algorithm, image):\\n'
            '    """Run the selected DRE algorithm through the adapter boundary."""\\n'
            '    # The fixed adapter fills residual_map for new algorithms that omit it.\\n'
            '    result = algorithm.process(image)\\n'
            '    if "residual_map" not in result:\\n'
            '        result["residual_map"] = 0.0\\n'
            '    return result\\n',
            encoding="utf-8",
        )
        config.write_text(json.dumps({"dre_algorithm": "new_llf"}), encoding="utf-8")
        for module in ["main", "pipeline", "modules.dre_adapter"]:
            if module in sys.modules:
                del sys.modules[module]
        assert importlib.import_module("main").run()["metadata"]["algorithm"] == "new_llf"
    finally:
        config.write_text(original_config, encoding="utf-8")
        adapter.write_text(original_adapter, encoding="utf-8")
''',
    "scripts/build.sh": "#!/usr/bin/env bash\nset -euo pipefail\npython -m compileall examples/demo_project/src\n",
    "scripts/run_demo.sh": "#!/usr/bin/env bash\nset -euo pipefail\npython examples/demo_project/src/main.py\n",
}


def reset_demo_project(mode: str = "old") -> None:
    """Reset demo_project to its initial or fixed teaching state."""
    # The CLI calls this before demos so repeated runs stay deterministic.
    for relative, content in FILES.items():
        path = DEMO_PROJECT_DIR / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if mode == "new_fixed":
        (DEMO_PROJECT_DIR / "src/modules/dre_adapter.py").write_text(
            'def run_dre(algorithm, image):\n'
            '    """Run the selected DRE algorithm through the adapter boundary."""\n'
            '    # The fixed adapter fills residual_map for new algorithms that omit it.\n'
            '    result = algorithm.process(image)\n'
            '    if "residual_map" not in result:\n'
            '        result["residual_map"] = 0.0\n'
            '    return result\n',
            encoding="utf-8",
        )
        (DEMO_PROJECT_DIR / "config/pipeline.json").write_text('{\n  "dre_algorithm": "new_llf"\n}\n', encoding="utf-8")

