import json
from pathlib import Path


def legacy_ranker(items):
    """Return the legacy ranking and downstream metadata contract."""
    return [{"id": item["id"], "score": item["quality"],
             "metadata": {"confidence": 1.0, "reason": "legacy quality"}} for item in items]


def neural_scorer(items):
    """Return the new scoring algorithm's native output schema."""
    return [{"id": item["id"], "value": 0.7 * item["quality"] + 0.3 * item["relevance"],
             "confidence": 0.95, "explanation": "quality and relevance"} for item in items]


def rank(items, algorithm=None):
    """Select the configured algorithm and produce ranked items."""
    active = algorithm or json.loads(Path(__file__).with_name("config.json").read_text())["algorithm"]
    if active == "LegacyRanker":
        rows = legacy_ranker(items)
    elif active == "NeuralScorer":
        rows = neural_scorer(items)
    else:
        raise ValueError(f"Unknown algorithm: {active}")
    return {"algorithm": active, "items": sorted(rows, key=lambda row: row["score"], reverse=True)}
