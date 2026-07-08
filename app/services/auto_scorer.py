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
from app.db.mongo import get_collection, get_predictions_collection, MongoPredictionRepository
from app.services.batch import score_batch_documents, to_storage_documents

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
    transactions_collection = get_collection()
    prediction_repository = MongoPredictionRepository()

    already_scored = _get_already_scored_object_ids()

    query = {}
    if already_scored:
        query["_id"] = {"$nin": list(already_scored)}

    new_documents = list(transactions_collection.find(query))
    if not new_documents:
        return

    # Convert ObjectId -> str so TransactionRecord (which expects a str
    # for its "_id"-aliased id field) validates correctly — the same
    # conversion MongoTransactionRepository.fetch_transactions() does.
    for doc in new_documents:
        doc["_id"] = str(doc["_id"])

    logger.info("Auto-scorer found %d new transaction(s) to score", len(new_documents))

    predictions, _summary = score_batch_documents(new_documents)

    now = datetime.now(timezone.utc)
    storage_docs = to_storage_documents(predictions, timestamp=now)

    saved_count = prediction_repository.save_predictions(storage_docs)
    logger.info("Auto-scorer saved %d new predictions to fraud_predictions", saved_count)


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