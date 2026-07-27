"""Shared adjustments applied to calculated training scores."""


def apply_over_1200_score_reduction(training_results, config, current_stats):
    """Return results with the configured score penalty applied above 1200.

    A shallow copy is used so callers and diagnostic output retaining the
    original calculated scores are not modified.
    """
    if not config.get("over_1200_score_reduction_enabled", False):
        return training_results

    try:
        reduction = max(0.0, float(config.get("over_1200_score_reduction", 0)))
    except (TypeError, ValueError):
        reduction = 0.0
    if reduction == 0 or not isinstance(current_stats, dict):
        return training_results

    adjusted = {}
    for stat, result in training_results.items():
        result_copy = dict(result)
        result_copy["raw_score"] = result_copy.get("score", 0)
        result_copy["score_reduction"] = 0.0
        if stat in ("spd", "sta", "pwr", "guts", "wit"):
            try:
                is_over_threshold = float(current_stats.get(stat, 0)) > 1200
            except (TypeError, ValueError):
                is_over_threshold = False
            if is_over_threshold:
                try:
                    score = float(result_copy.get("score", 0))
                except (TypeError, ValueError):
                    score = 0.0
                effective_score = round(max(0.0, score - reduction), 2)
                result_copy["score"] = effective_score
                result_copy["score_reduction"] = round(score - effective_score, 2)
        adjusted[stat] = result_copy
    return adjusted


def format_training_score_evaluation(training_results, current_stats, min_scores):
    """Build compact, aligned log lines for the scores used by selection."""
    lines = ["--- Training Score Evaluation (effective scores) ---"]
    stats = current_stats if isinstance(current_stats, dict) else {}
    for stat in ("spd", "sta", "pwr", "guts", "wit"):
        result = training_results.get(stat)
        if not result:
            continue
        stat_value = stats.get(stat, "?")
        if result.get("skipped"):
            lines.append(
                f"  {stat.upper():>4} | Stat {str(stat_value):>4} | SKIPPED by stat cap"
            )
            continue

        raw = float(result.get("raw_score", result.get("score", 0)))
        effective = float(result.get("score", 0))
        reduction = float(result.get("score_reduction", 0))
        minimum = float(min_scores.get(stat, 1.0))
        failure = result.get("failure", "?")
        score_text = f"{raw:>4.2f}"
        if reduction > 0:
            score_text += f" - {reduction:.2f} penalty = {effective:.2f}"
        else:
            score_text += f" (no penalty)"
        eligibility = "PASS" if effective >= minimum else "BELOW MIN"
        lines.append(
            f"  {stat.upper():>4} | Stat {str(stat_value):>4} | "
            f"Score {score_text:<27} | Min {minimum:.2f} [{eligibility}] | Fail {failure}%"
        )
    return lines
