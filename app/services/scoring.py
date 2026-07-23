"""
Shared scoring helper used by both single-record and batch prediction paths.
"""

from typing import Dict

from app.services.ensemble import ensemble_predict
from app.services.ml import MODEL_VERSION, ml_score
from app.services.rules import rule_based_score


def score_transaction(data: dict) -> Dict:
    rule_score, triggered_rules, hard_block = rule_based_score(data)
    ml_res = ml_score(data)
    fraud_score = ml_res["fraud_score"]
    result = ensemble_predict(rule_score, fraud_score, hard_block)

    is_fraud = result["decision"] != "ALLOW"
    label = ml_res.get("label", 1 if is_fraud else 0)

    return {
        "subscriber_id": data["subscriber_id"],
        "is_fraud": is_fraud,
        "label": label,
        "rule_score": round(rule_score, 4),
        "fraud_score": round(fraud_score, 4),
        "ml_score": round(fraud_score, 4),
        "raw_score": round(ml_res.get("raw_score", 0.0), 4),
        "final_score": result["final_score"],
        "decision": result["decision"],
        "triggered_rules": triggered_rules,
        "model_version": ml_res.get("model_version", MODEL_VERSION),
    }