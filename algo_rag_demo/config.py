from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = EXAMPLES_DIR / "data"
CASE_DIR = DATA_DIR / "cases"
RAW_DIR = DATA_DIR / "raw"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
INDEX_DIR = OUTPUTS_DIR / "index"
DEMO_PROJECT_DIR = EXAMPLES_DIR / "demo_project"
RUNS_DIR = OUTPUTS_DIR / "runs"
SKILL_FILE = EXAMPLES_DIR / "skills" / "algorithm_replacement.md"

