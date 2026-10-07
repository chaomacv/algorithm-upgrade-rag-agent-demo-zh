from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CONFIG_DIR = PROJECT_ROOT / "configs"
CUSTOM_DATA_DIR = EXAMPLES_DIR / "custom_data"
CASE_DIR = CUSTOM_DATA_DIR / "cases"
RAW_DIR = CUSTOM_DATA_DIR / "raw"
KNOWLEDGE_DIR = OUTPUTS_DIR / "knowledge"
INDEX_DIR = OUTPUTS_DIR / "index"
RUNS_DIR = OUTPUTS_DIR / "runs"
DEFAULT_CONFIG = CONFIG_DIR / "deepseek_bge_m3.json"

