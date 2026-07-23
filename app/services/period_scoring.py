"""
On-demand period scoring.

The user picks start_time/end_time on the dashboard. This module:

1. Pulls every transaction whose record_opening_time is in that window.
2. Builds one subscriber profile per subscriber, using ONLY those
   transactions (not their whole history).
3. Saves those profiles into `subscriber_profile` — this OVERWRITES
   whatever was there before for those subscribers, because the
   profile should always reflect the period you just asked for.
4. Scores every profile with the same rule engine + Isolation Forest
   used everywhere else.
5. Saves the predictions into `fraud_predictions`, tagged with the
   period so you can tell batches apart later.
6. Returns everything the dashboard needs right away — no need to
   query MongoDB again.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.db.mongo import MongoTransactionRepository, MongoPredictionRepository
from app.services.batch import (
    build_subscriber_profiles_from_transactions,
    score_batch_documents,
    to_storage_documents,
)
from app.models.schemas import FraudRecordSummary, TriggeredRuleStat, TimeRangeStatsResponse

# Only these fields exist on FraudRecordSummary - anything else
# (like document_id, model_version) gets dropped before building it.
_RECORD_FIELDS = {
    "subscriber_id", "decision", "label", "is_fraud", "fraud_score",
    "ml_score", "raw_score", "rule_score", "final_score", "triggered_rules",
}


def _compute_rule_breakdown(predictions) -> List[TriggeredRuleStat]:
    totals: Dict[str, int] = {}
    fraud_counts: Dict[str, int] = {}

    for prediction in predictions:
        for rule in prediction.triggered_rules:
            totals[rule] = totals.get(rule, 0) + 1
            if prediction.is_fraud:
                fraud_counts[rule] = fraud_counts.get(rule, 0) + 1

    breakdown = []
    for rule, total in totals.items():
        fraud_count = fraud_counts.get(rule, 0)
        breakdown.append(
            TriggeredRuleStat(
                rule=rule,
                total=total,
                fraud_count=fraud_count,
                fraud_percentage=round((fraud_count / total) * 100, 2) if total else 0.0,
            )
        )

    breakdown.sort(key=lambda r: r.total, reverse=True)
    return breakdown


def build_and_score_period(
    start_time: datetime,
    end_time: datetime,
    transactions_collection_name: Optional[str] = None,
    profile_collection_name: str = "subscriber_profile",
) -> TimeRangeStatsResponse:
    transaction_repository = MongoTransactionRepository()
    prediction_repository = MongoPredictionRepository()

    # Step 1: only the transactions inside the window the user picked
    transactions = transaction_repository.fetch_transactions_by_time_range(
        start_time=start_time,
        end_time=end_time,
        collection_name=transactions_collection_name,
    )

    if not transactions:
        return TimeRangeStatsResponse(
            start_time=start_time,
            end_time=end_time,
            total_records=0,
            fraud_count=0,
            normal_count=0,
            fraud_percentage=0.0,
            normal_percentage=0.0,
            records=[],
            rule_breakdown=[],
        )

    # Step 2: one profile per subscriber, built ONLY from this window
    profile_docs = build_subscriber_profiles_from_transactions(transactions)

    # Step 3: save/overwrite subscriber_profile with this window's numbers
    transaction_repository.save_subscriber_profiles(
        profile_docs, collection_name=profile_collection_name
    )

    # Step 4: score every profile (rule engine + Isolation Forest)
    predictions, _summary = score_batch_documents(profile_docs)

    # Step 5: save predictions, tagged with the period they came from
    now = datetime.now(timezone.utc)
    storage_docs = to_storage_documents(predictions, timestamp=now)
    for doc in storage_docs:
        doc["period_start"] = start_time
        doc["period_end"] = end_time
    prediction_repository.save_predictions(storage_docs)

    # Step 6: build the dashboard response straight from what we just did
    total = len(predictions)
    fraud_count = sum(1 for p in predictions if p.is_fraud)
    normal_count = total - fraud_count

    records = []
    for prediction in predictions:
        doc = {k: v for k, v in prediction.model_dump().items() if k in _RECORD_FIELDS}
        doc["created_at"] = now
        records.append(FraudRecordSummary(**doc))

    return TimeRangeStatsResponse(
        start_time=start_time,
        end_time=end_time,
        total_records=total,
        fraud_count=fraud_count,
        normal_count=normal_count,
        fraud_percentage=round((fraud_count / total) * 100, 2) if total else 0.0,
        normal_percentage=round((normal_count / total) * 100, 2) if total else 0.0,
        records=records,
        rule_breakdown=_compute_rule_breakdown(predictions),
    )