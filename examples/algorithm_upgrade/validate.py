import json
import sys

from ranking import rank


ITEMS = [
    {"id": "a", "quality": 0.9, "relevance": 0.1},
    {"id": "b", "quality": 0.7, "relevance": 1.0},
]


def check_interface():
    """Verify downstream fields and scalar types remain compatible."""
    result = rank(ITEMS)
    assert len(result["items"]) == 2, "Expected one result per input."
    for row in result["items"]:
        assert isinstance(row["id"], str)
        assert isinstance(row["score"], (int, float)), "Missing numeric score."
        assert isinstance(row["metadata"]["confidence"], (int, float))
        assert isinstance(row["metadata"]["reason"], str), "Missing metadata.reason."


def check_runtime():
    """Verify that the configured new algorithm is actually active."""
    assert rank(ITEMS)["algorithm"] == "NeuralScorer", "Runtime still uses LegacyRanker."


def check_regression():
    """Verify the new algorithm's ranking and numeric scores."""
    rows = rank(ITEMS)["items"]
    assert [row["id"] for row in rows] == ["b", "a"], "New scorer must rank b above a."
    expected = {"a": 0.66, "b": 0.79}
    for row in rows:
        assert abs(row["score"] - expected[row["id"]]) < 1e-8, "Incorrect NeuralScorer score."
    assert rank([])["items"] == [], "Empty input regression."


def check_rollback():
    """Verify the legacy algorithm remains callable with its original result."""
    result = rank(ITEMS, algorithm="LegacyRanker")
    assert result["algorithm"] == "LegacyRanker"
    assert [row["id"] for row in result["items"]] == ["a", "b"]
    assert result["items"][0]["score"] == 0.9
    assert result["items"][0]["metadata"]["reason"] == "legacy quality"


def main():
    """Run independent checks and emit machine-readable validation evidence."""
    checks = []
    for check in [check_interface, check_runtime, check_regression, check_rollback]:
        try:
            check()
            checks.append({"name": check.__name__, "passed": True})
        except Exception as exc:
            checks.append({"name": check.__name__, "passed": False, "error": str(exc)})
    passed = all(check["passed"] for check in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
