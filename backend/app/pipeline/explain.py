from typing import List, Tuple, Dict, Any

VERDICT_LABELS = {
    "low_risk": "Low Risk",
    "needs_verification": "Needs Verification",
    "high_suspicion": "High Suspicion",
    "insufficient_quality": "Insufficient Quality"
}

def generate_explanation(
    verdict: str,
    reasons: List[str],
    layers_executed: List[str],
    all_possible_layers: List[str],
    quality_passed: bool
) -> Tuple[str, float, str, List[str], List[str]]:
    """
    Generates verdict_label, confidence, confidence_note, checked, and not_checked arrays.
    """
    verdict_label = VERDICT_LABELS.get(verdict, "Needs Verification")

    checked = [layer for layer in all_possible_layers if layer in layers_executed]
    not_checked = [layer for layer in all_possible_layers if layer not in layers_executed]

    if not quality_passed or verdict == "insufficient_quality":
        confidence = 0.0
        confidence_note = "Image quality checks failed prior to analysis."
    elif verdict == "low_risk":
        confidence = round(85.0 + (len(checked) * 3.0), 1)
        confidence = min(98.0, confidence)
        confidence_note = f"All {len(checked)} analysis layers evaluated with high consistency."
    elif verdict == "high_suspicion":
        confidence = 90.0
        confidence_note = "Strong inconsistency or high risk anomaly detected."
    else:  # needs_verification
        confidence = 65.0
        confidence_note = "Certain verification layers yielded ambiguous or incomplete evidence."

    return verdict_label, confidence, confidence_note, checked, not_checked
