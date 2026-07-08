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
    fraud_count = sum(1 for prediction in predictions if prediction.is_fraud)

    if total_records == 0:
        return BatchPredictionSummary(
            total_records=0, fraud_count=0, not_fraud_count=0,
            average_rule_score=0.0, average_ml_score=0.0, average_final_score=0.0,
        )

    return BatchPredictionSummary(
        total_records=total_records,
        fraud_count=fraud_count,
        not_fraud_count=total_records - fraud_count,
        average_rule_score=round(sum(item.rule_score for item in predictions) / total_records, 4),
        average_ml_score=round(sum(item.ml_score for item in predictions) / total_records, 4),
        average_final_score=round(sum(item.final_score for item in predictions) / total_records, 4),
    )


def score_batch_documents(documents: Iterable[dict]) -> Tuple[List[BatchPredictionItem], BatchPredictionSummary]:
    predictions: List[BatchPredictionItem] = []

    for document in documents:
        transaction = TransactionRecord.model_validate(document)
        transaction_data = transaction.model_dump(exclude={"id"})
        scored = score_transaction(transaction_data)
        predictions.append(
            BatchPredictionItem(
                document_id=str(transaction.id) if transaction.id is not None else None,
                is_fraud=scored["decision"] != "ALLOW",
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