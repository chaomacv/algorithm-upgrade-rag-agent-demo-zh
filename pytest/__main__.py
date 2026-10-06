import importlib.util
import inspect
import sys
import traceback
from pathlib import Path


def _iter_test_files(root: Path):
    """Yield demo test files from the main and toy project test folders."""
    # The fallback runner intentionally ignores generated runs directories.
    for base in [root / "tests", root / "examples" / "demo_project" / "tests"]:
        if base.exists():
            yield from sorted(base.glob("test_*.py"))


def _load(path: Path):
    """Load one test file as an isolated module."""
    # Unique module names avoid collisions between same-named test files.
    name = "_demo_test_" + "_".join(path.with_suffix("").parts[-4:])
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """Run simple test_* functions and return a pytest-like exit code."""
    # This fallback supports only the project's plain assert-style tests.
    root = Path.cwd()
    total = 0
    failed = 0
    for path in _iter_test_files(root):
        module = _load(path)
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                fn()
            except Exception:
                failed += 1
                print(f"FAILED {path}:{name}")
                traceback.print_exc()
    if failed:
        print(f"{failed} failed, {total - failed} passed")
        return 1
    print(f"{total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

