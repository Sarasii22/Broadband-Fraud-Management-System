"""
Combines the rule-based score and the Isolation Forest anomaly score
to produce the final fraud decision.

Workflow

Rule Engine
      ↓
Rule Score (0-1)
      ↓
Isolation Forest
      ↓
Fraud Score (0-1)
      ↓
Weighted Average
      ↓
Final Decision
"""

from typing import Dict

# ==========================================================
# Weights
# ==========================================================

RULE_WEIGHT = 0.40
ML_WEIGHT = 0.60

# ==========================================================
# Decision Thresholds
# ==========================================================

BLOCK_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.45


def ensemble_predict(
    rule_score: float,
    fraud_score: float,
    hard_block: bool = False
) -> Dict:
    """
    Combine rule score and ML fraud score.

    Parameters
    ----------
    rule_score : float
        Score from the rule engine (0-1)

    fraud_score : float
        Normalized anomaly score from Isolation Forest (0-1)

    hard_block : bool
        Immediately block if a critical rule is triggered.

    Returns
    -------
    {
        "rule_score": ...,
        "ml_score": ...,
        "final_score": ...,
        "decision": ...
    }
    """

    # ------------------------------------------------------
    # Hard Block
    # ------------------------------------------------------

    if hard_block:
        return {
            "rule_score": round(rule_score, 4),
            "ml_score": round(fraud_score, 4),
            "final_score": 1.0,
            "decision": "BLOCK"
        }

    # ------------------------------------------------------
    # Weighted Score
    # ------------------------------------------------------

    final_score = (
        RULE_WEIGHT * rule_score
        + ML_WEIGHT * fraud_score
    )

    # ------------------------------------------------------
    # Final Decision
    # ------------------------------------------------------

    if final_score >= BLOCK_THRESHOLD:
        decision = "BLOCK"

    elif final_score >= REVIEW_THRESHOLD:
        decision = "REVIEW"

    else:
        decision = "ALLOW"

    return {
        "rule_score": round(rule_score, 4),
        "ml_score": round(fraud_score, 4),
        "final_score": round(final_score, 4),
        "decision": decision
    }