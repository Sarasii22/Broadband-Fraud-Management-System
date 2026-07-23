"""
Background auto-scoring poller.

Instead of requiring a manual POST /predict call after adding data,
this periodically checks the `transactions` collection for documents
that haven't been scored yet (i.e. their _id doesn't appear as a
document_id in fraud_predictions), scores them using the exact same
logic as /predict, and saves the results with a timestamp.

This means: however you add data (a script, MongoDB Compass, mongosh,
an API endpoint) — as long as it lands in `transactions`, it gets
picked up and scored automatically within POLL_INTERVAL_SECONDS.
"""

import threading
from datetime import datetime, timezone
from typing import Set

from bson import ObjectId

from app.core.logging import setup_logging
from app.db.mongo import (
    get_collection,
    get_predictions_collection,
    MongoTransactionRepository,
    MongoPredictionRepository,
)
from app.services.batch import (
    build_subscriber_profiles_from_transactions,
    score_batch_documents,
    to_storage_documents,
)

logger = setup_logging()

POLL_INTERVAL_SECONDS = 5

_stop_event = threading.Event()
_thread = None


def _get_already_scored_object_ids() -> Set[ObjectId]:
    """
    Returns the set of transaction _ids that already have a
    corresponding entry in fraud_predictions (via document_id).
    """
    predictions_collection = get_predictions_collection()
    doc_ids = predictions_collection.distinct("document_id")

    object_ids: Set[ObjectId] = set()
    for doc_id in doc_ids:
        if not doc_id:
            continue
        try:
            object_ids.add(ObjectId(doc_id))
        except Exception:
            # Skip anything that isn't a valid ObjectId string
            continue
    return object_ids


def _score_new_transactions() -> None:
    transactions_collection = get_collection("transactions")
    transaction_repository = MongoTransactionRepository()
    prediction_repository = MongoPredictionRepository()

    already_scored = _get_already_scored_object_ids()

    query = {}
    if already_scored:
        query["_id"] = {"$nin": list(already_scored)}

    new_documents = list(transactions_collection.find(query))
    if not new_documents:
        return

    for doc in new_documents:
        doc["_id"] = str(doc["_id"])

    logger.info("Auto-scorer found %d new transaction(s)", len(new_documents))

    affected_subscriber_ids = {d["subscriber_id"] for d in new_documents if d.get("subscriber_id")}

    full_docs = list(
        transactions_collection.find({"subscriber_id": {"$in": list(affected_subscriber_ids)}})
    )
    for doc in full_docs:
        doc["_id"] = str(doc["_id"])

    profile_docs = build_subscriber_profiles_from_transactions(full_docs)

    saved_profiles = transaction_repository.save_subscriber_profiles(
        profile_docs, collection_name="subscriber_profile"
    )
    logger.info("Auto-scorer updated %d subscriber profile(s)", saved_profiles)

    predictions, _summary = score_batch_documents(profile_docs)

    now = datetime.now(timezone.utc)
    storage_docs = to_storage_documents(predictions, timestamp=now)

    new_ids = [d["_id"] for d in new_documents]
    for storage_doc, new_id in zip(storage_docs, new_ids):
        storage_doc["document_id"] = new_id

    saved_count = prediction_repository.save_predictions(storage_docs)
    logger.info("Auto-scorer saved %d new predictions", saved_count)

def _poll_loop(stop_event: threading.Event) -> None:
    logger.info("Auto-scorer background poller started (interval=%ss)", POLL_INTERVAL_SECONDS)
    while not stop_event.is_set():
        try:
            _score_new_transactions()
        except Exception:
            logger.exception("Auto-scorer poll iteration failed")
        stop_event.wait(POLL_INTERVAL_SECONDS)
    logger.info("Auto-scorer background poller stopped")


def start_auto_scorer() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_poll_loop, args=(_stop_event,), daemon=True)
    _thread.start()


def stop_auto_scorer() -> None:
    _stop_event.set()