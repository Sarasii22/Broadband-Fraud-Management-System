"""
MongoDB connection helpers and repositories for stored transactions
and scored predictions.
"""

import os
import importlib
from datetime import datetime
from typing import Any, Optional, List, Dict

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)

DEFAULT_MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_MONGODB_DB = os.getenv("MONGODB_DB", "fraud_api")
DEFAULT_MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "transactions")

DEFAULT_PREDICTIONS_COLLECTION = os.getenv("MONGODB_PREDICTIONS_COLLECTION", "fraud_predictions")

_client: Optional[Any] = None


def get_client() -> Any:
    global _client
    if _client is None:
        try:
            pymongo = importlib.import_module("pymongo")
        except ModuleNotFoundError as exc:
            raise RuntimeError("pymongo is not installed. Install requirements.txt to use MongoDB-backed endpoints.") from exc
        _client = pymongo.MongoClient(DEFAULT_MONGODB_URI)
    return _client


def get_database():
    return get_client()[DEFAULT_MONGODB_DB]


def get_collection(collection_name: Optional[str] = None):
    return get_database()[collection_name or DEFAULT_MONGODB_COLLECTION]


def get_predictions_collection(collection_name: Optional[str] = None):
    return get_database()[collection_name or DEFAULT_PREDICTIONS_COLLECTION]


class MongoTransactionRepository:
    def fetch_transactions(self, collection_name: Optional[str] = None, customer_id: Optional[str] = None, skip: int = 0, limit: Optional[int] = None):
        query = {}
        if customer_id:
            query["customer_id"] = customer_id

        cursor = get_collection(collection_name).find(query).sort("_id", 1).skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        return documents

    def fetch_transactions_by_customer_id(
        self,
        customer_id: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        cursor = get_collection(collection_name).find({"customer_id": customer_id}).sort("_id", -1)
        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        return documents


class MongoPredictionRepository:
    """
    Handles writing scored results automatically, and reading them back
    grouped by time period via an aggregation pipeline.
    """

    def ensure_indexes(self, collection_name: Optional[str] = None) -> None:
        get_predictions_collection(collection_name).create_index("created_at")
        get_predictions_collection(collection_name).create_index("customer_id")
        get_predictions_collection(collection_name).create_index("document_id")

    def save_predictions(self, predictions: List[Dict], collection_name: Optional[str] = None) -> int:
        if not predictions:
            return 0
        collection = get_predictions_collection(collection_name)
        result = collection.insert_many(predictions)
        return len(result.inserted_ids)

    def fetch_predictions_by_customer_id(
        self,
        customer_id: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        cursor = get_predictions_collection(collection_name).find({"customer_id": customer_id}).sort("created_at", -1)
        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return documents

    def fetch_stats_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        collection_name: Optional[str] = None,
    ) -> Dict:
        collection = get_predictions_collection(collection_name)

        pipeline = [
            {"$match": {"created_at": {"$gte": start_time, "$lte": end_time}}},
            {
                "$facet": {
                    # Overall fraud vs normal counts
                    "summary": [
                        {"$group": {"_id": "$is_fraud", "count": {"$sum": 1}}}
                    ],
                    # Individual records for the table view
                    "records": [
                        {"$sort": {"created_at": -1}},
                        {
                            "$project": {
                                "_id": 0,
                                "customer_id": 1,
                                "is_fraud": 1,
                                "decision": 1,
                                "final_score": 1,
                                "rule_score": 1,
                                "ml_score": 1,
                                "triggered_rules": 1,
                                "created_at": 1,
                            }
                        },
                    ],
                    # NEW: per-rule breakdown — how many times each rule
                    # fired in this period, and what fraction of those
                    # firings were confirmed fraud.
                    "rule_breakdown": [
                        {"$unwind": "$triggered_rules"},
                        {
                            "$group": {
                                "_id": "$triggered_rules",
                                "total": {"$sum": 1},
                                "fraud_count": {
                                    "$sum": {"$cond": ["$is_fraud", 1, 0]}
                                },
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "rule": "$_id",
                                "total": 1,
                                "fraud_count": 1,
                                "fraud_percentage": {
                                    "$cond": [
                                        {"$eq": ["$total", 0]},
                                        0,
                                        {
                                            "$multiply": [
                                                {"$divide": ["$fraud_count", "$total"]},
                                                100,
                                            ]
                                        },
                                    ]
                                },
                            }
                        },
                        {"$sort": {"total": -1}},
                    ],
                }
            },
        ]

        result = list(collection.aggregate(pipeline))
        return result[0] if result else {"summary": [], "records": [], "rule_breakdown": []}