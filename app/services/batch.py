"""
Batch scoring helpers for MongoDB-backed transaction collections.
"""

from datetime import datetime, timezone
from typing import Iterable, List, Tuple, Dict, Optional

from app.models.schemas import (
    BatchPredictionItem,
    BatchPredictionSummary,
    TransactionRecord,
)
from app.services.scoring import score_transaction


def build_batch_summary(predictions: List[BatchPredictionItem]) -> BatchPredictionSummary:
    total_records = len(predictions)
    fraud_count = sum(1 for p in predictions if getattr(p, "is_fraud", p.label == 1))
    not_fraud = total_records - fraud_count

    if total_records == 0:
        return BatchPredictionSummary(
            total_records=0,
            fraud_count=0,
            normal_count=0,
            not_fraud_count=0,
            average_rule_score=0.0,
            average_fraud_score=0.0,
            average_ml_score=0.0,
            average_final_score=0.0,
        )

    avg_rule = round(sum(p.rule_score for p in predictions) / total_records, 4)
    avg_ml = round(sum(getattr(p, "fraud_score", getattr(p, "ml_score", 0.0)) or getattr(p, "ml_score", 0.0) for p in predictions) / total_records, 4)
    avg_final = round(sum(p.final_score for p in predictions) / total_records, 4)

    return BatchPredictionSummary(
        total_records=total_records,
        fraud_count=fraud_count,
        normal_count=not_fraud,
        not_fraud_count=not_fraud,
        average_rule_score=avg_rule,
        average_fraud_score=avg_ml,
        average_ml_score=avg_ml,
        average_final_score=avg_final,
    )


def score_batch_documents(documents: Iterable[dict]) -> Tuple[List[BatchPredictionItem], BatchPredictionSummary]:
    predictions: List[BatchPredictionItem] = []

    for document in documents:
        transaction = TransactionRecord.model_validate(document)
        scored = score_transaction(transaction.to_scoring_payload())
        predictions.append(
            BatchPredictionItem(
                document_id=str(transaction.id) if transaction.id is not None else None,
                **scored,
            )
        )

    return predictions, build_batch_summary(predictions)


def to_storage_documents(
    predictions: List[BatchPredictionItem],
    timestamp: Optional[datetime] = None,
) -> List[Dict]:
    """
    Converts scored predictions into plain dicts ready to insert into
    the fraud_predictions collection, stamping them all with the same
    `created_at` time (the moment this batch was scored).
    """
    ts = timestamp or datetime.now(timezone.utc)
    docs = []
    for prediction in predictions:
        doc = prediction.model_dump()
        doc["created_at"] = ts
        docs.append(doc)
    return docs


def build_subscriber_profiles_from_transactions(documents: Iterable[dict]) -> List[Dict]:
    """
    Aggregates raw transaction session documents grouped by subscriber_id,
    calculating download MB, upload MB, total usage MB, avg usage MB, max usage MB,
    and total session counts.
    """
    profiles_by_sub: Dict[str, Dict] = {}

    for doc in documents:
        sub_id = doc.get("subscriber_id")
        if not sub_id:
            continue

        trans = TransactionRecord.model_validate(doc)
        payload = trans.to_scoring_payload()

        download_mb = float(payload.get("total_download_mb", 0.0) or 0.0)
        upload_mb = float(payload.get("total_upload_mb", 0.0) or 0.0)
        usage_mb = float(payload.get("total_usage_mb", payload.get("usage_mb", 0.0)) or 0.0)

        if sub_id not in profiles_by_sub:
            profiles_by_sub[sub_id] = {
                "subscriber_id": sub_id,
                "total_download_mb": 0.0,
                "total_upload_mb": 0.0,
                "total_usage_mb": 0.0,
                "usages": [],
                "Number_of_sessions": 0,
            }

        prof = profiles_by_sub[sub_id]
        prof["total_download_mb"] += download_mb
        prof["total_upload_mb"] += upload_mb
        prof["total_usage_mb"] += usage_mb
        prof["usages"].append(usage_mb)
        prof["Number_of_sessions"] += 1

    profile_docs: List[Dict] = []
    for sub_id, prof in profiles_by_sub.items():
        total_usage = round(prof["total_usage_mb"], 4)
        sessions = prof["Number_of_sessions"]
        usages = prof["usages"]
        avg_usage = round(total_usage / sessions, 4) if sessions > 0 else 0.0
        max_usage = round(max(usages), 4) if usages else 0.0

        profile_docs.append({
            "subscriber_id": sub_id,
            "total_download_mb": round(prof["total_download_mb"], 4),
            "total_upload_mb": round(prof["total_upload_mb"], 4),
            "total_usage_mb": total_usage,
            "avg_usage_mb": avg_usage,
            "max_usage_mb": max_usage,
            "Number_of_sessions": sessions,
        })

    return profile_docs