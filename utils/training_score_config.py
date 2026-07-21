"""Shared loading and phase selection for training-score configuration."""

import json
import os


SCORE_DIRECTORY = os.path.join("template", "training_score")
SCORE_FILENAMES = {
    "ura": "training_score.json",
    "unity": "training_score_unity.json",
    "trackblazer": "training_score_trackblazer.json",
}


def get_training_score_path(project_root, mode):
    """Return the score configuration path for a scenario mode."""
    filename = SCORE_FILENAMES.get(mode, SCORE_FILENAMES["ura"])
    return os.path.join(project_root, SCORE_DIRECTORY, filename)


def get_training_score_profile(year):
    """Map the detected career date to an advanced score profile."""
    value = str(year or "").strip()
    lower = value.lower()
    parts = value.split()

    # Summer camp overrides Classic/Senior profiles. Junior July/August is not camp.
    if "junior" not in lower and any(part in ("Jul", "Aug") for part in parts):
        return "summer"
    if "junior" in lower or "pre-debut" in lower or "predebut" in lower:
        return "junior"
    if "classic" in lower:
        return "classic"
    if "senior" in lower:
        return "senior"
    if "finale" in lower or "twinkle" in lower or "ts climax" in lower or "year 4" in lower:
        return "finale"
    return None


def load_training_score_rules(project_root, mode, year=None):
    """Load base rules, or a matching advanced profile when enabled."""
    path = get_training_score_path(project_root, mode)
    with open(path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    base_rules = config.get("scoring_rules", {})
    if not config.get("advanced_enabled", False):
        return base_rules

    profile = get_training_score_profile(year)
    profile_rules = config.get("profiles", {}).get(profile, {}) if profile else {}
    return profile_rules or base_rules
