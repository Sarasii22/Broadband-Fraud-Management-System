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
    """
    Repository for subscriber profile documents.

    Example document:

    {
        "subscriber_id": "SUB_2922DC01",
        "total_download_mb": 562.61,
        "total_upload_mb": 44.52,
        "total_usage_mb": 607.14,
        "avg_usage_mb": 67.46,
        "max_usage_mb": 120.76,
        "Number_of_sessions": 9
    }
    """

    def fetch_transactions(
        self,
        collection_name: Optional[str] = None,
        subscriber_id: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ):
        query = {}

        if subscriber_id:
            query["subscriber_id"] = subscriber_id

        cursor = (
            get_collection(collection_name)
            .find(query)
            .sort("_id", 1)
            .skip(skip)
        )

        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)

        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return documents

    def fetch_transactions_by_subscriber_id(
        self,
        subscriber_id: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        cursor = (
            get_collection(collection_name)
            .find({"subscriber_id": subscriber_id})
            .sort("_id", -1)
        )

        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)

        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return documents

    def save_subscriber_profiles(
        self,
        profiles: List[Dict],
        collection_name: str = "subscriber_profile",
    ) -> int:
        if not profiles:
            return 0
        collection = get_database()[collection_name]
        updated_count = 0
        for profile in profiles:
            sub_id = profile.get("subscriber_id")
            if sub_id:
                collection.update_one(
                    {"subscriber_id": sub_id},
                    {"$set": profile},
                    upsert=True
                )
                updated_count += 1
        return updated_count
    



class MongoPredictionRepository:
    """
    Handles storing prediction results and retrieving them for
    dashboards, reports, and subscriber history.

    This repository works with the Isolation Forest prediction output.
    """

    def ensure_indexes(self, collection_name: Optional[str] = None) -> None:
        """
        Create indexes for faster searching.
        """

        collection = get_predictions_collection(collection_name)

        collection.create_index("created_at")
        collection.create_index("subscriber_id")
        collection.create_index("document_id")

    # ---------------------------------------------------------

    def save_predictions(
        self,
        predictions: List[Dict],
        collection_name: Optional[str] = None,
    ) -> int:
        """
        Save prediction results into MongoDB.
        """

        if not predictions:
            return 0

        collection = get_predictions_collection(collection_name)

        result = collection.insert_many(predictions)

        return len(result.inserted_ids)

    # ---------------------------------------------------------

    def fetch_predictions_by_subscriber_id(
        self,
        subscriber_id: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        """
        Get prediction history for one subscriber.
        """

        cursor = (
            get_predictions_collection(collection_name)
            .find({"subscriber_id": subscriber_id})
            .sort("created_at", -1)
        )

        if limit is not None:
            cursor = cursor.limit(limit)

        documents = list(cursor)

        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return documents

    # ---------------------------------------------------------

    def fetch_stats_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        collection_name: Optional[str] = None,
    ) -> Dict:
        """
        Generate dashboard statistics within a time range.
        """

        collection = get_predictions_collection(collection_name)

        pipeline = [

            {
                "$match": {
                    "created_at": {
                        "$gte": start_time,
                        "$lte": end_time
                    }
                }
            },

            {
                "$facet": {

                    # -------------------------------
                    # Fraud vs Normal Summary
                    # -------------------------------

                    "summary": [
                        {
                            "$group": {
                                "_id": "$label",
                                "count": {
                                    "$sum": 1
                                }
                            }
                        }
                    ],

                    # -------------------------------
                    # Prediction Records
                    # -------------------------------

                    "records": [

                        {
                            "$sort": {
                                "created_at": -1
                            }
                        },

                        {
                            "$project": {

                                "_id": 0,

                                "subscriber_id": 1,

                                "decision": 1,

                                "label": 1,

                                "is_fraud": 1,

                                "fraud_score": 1,

                                "ml_score": 1,

                                "raw_score": 1,

                                "rule_score": 1,

                                "final_score": 1,

                                "triggered_rules": 1,

                                "created_at": 1,
                            }
                        }
                    ],

                    # -------------------------------
                    # Rule Breakdown
                    # -------------------------------

                    "rule_breakdown": [

                        {
                            "$unwind": "$triggered_rules"
                        },

                        {
                            "$group": {

                                "_id": "$triggered_rules",

                                "total": {
                                    "$sum": 1
                                },

                                "fraud_count": {

                                    "$sum": {

                                        "$cond": [
                                            {
                                                "$eq": [
                                                    "$label",
                                                    1
                                                ]
                                            },
                                            1,
                                            0
                                        ]
                                    }
                                }
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

                                        {
                                            "$eq": [
                                                "$total",
                                                0
                                            ]
                                        },

                                        0,

                                        {

                                            "$multiply": [

                                                {
                                                    "$divide": [
                                                        "$fraud_count",
                                                        "$total"
                                                    ]
                                                },

                                                100

                                            ]
                                        }

                                    ]
                                }

                            }
                        },

                        {
                            "$sort": {
                                "total": -1
                            }
                        }

                    ]
                }
            }
        ]

        result = list(collection.aggregate(pipeline))

        return result[0] if result else {
            "summary": [],
            "records": [],
            "rule_breakdown": []
        }