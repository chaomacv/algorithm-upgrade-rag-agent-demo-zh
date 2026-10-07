# Algorithm Replacement Skill

Inspect the current implementation and downstream contract before changing files.
Replace LegacyRanker with NeuralScorer through configuration and a schema adapter.
Keep neural_scorer and legacy_ranker implementations unchanged.
NeuralScorer returns value, confidence, explanation; downstream needs score and
metadata.confidence / metadata.reason. Map these fields without changing scores.
Preserve rank(items, algorithm=None), including an explicit LegacyRanker override.
Validation is independent of the planner: interface, runtime activation, exact
scores and ranking, empty input, and legacy fallback must pass.
Return write_file actions containing complete ranking.py and config.json contents.
Only ranking.py and config.json are editable. Never modify validate.py.
On failure, inspect actual process output and current files, then propose a repair.
