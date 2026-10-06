import json
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
