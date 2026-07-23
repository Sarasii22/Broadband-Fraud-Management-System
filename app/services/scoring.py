"""
Shared scoring helper used by both single-record and batch prediction paths.
"""

from typing import Dict

from app.services.ensemble import ensemble_predict
from app.services.ml import MODEL_VERSION, ml_score
from app.services.rules import rule_based_score


def score_transaction(data: dict) -> Dict:
    rule_score, triggered_rules, hard_block = rule_based_score(data)
    model_score = ml_score(data)
    result = ensemble_predict(rule_score, model_score, hard_block)

    return {
        "subscriber_id": data["subscriber_id"],
        "rule_score": round(rule_score, 4),
        "fraud_score": round(model_score, 4),
        "final_score": result["final_score"],
        "decision": result["decision"],
        "triggered_rules": triggered_rules,
        "model_version": MODEL_VERSION,
    }