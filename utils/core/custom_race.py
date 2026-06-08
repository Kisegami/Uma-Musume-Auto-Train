def get_custom_race_name(entry):
    """Return the race name from legacy string or editor-generated entries."""
    if isinstance(entry, dict):
        entry = entry.get("race", "")
    return entry.strip() if isinstance(entry, str) else ""
