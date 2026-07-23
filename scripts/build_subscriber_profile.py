from argparse import ArgumentParser
from pathlib import Path
from typing import List

import pandas as pd
from pymongo import MongoClient, ReplaceOne


def _parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Build per-subscriber profile aggregates from MongoDB transactions.")
    parser.add_argument(
        "--database",
        default="fraud_api",
        help="MongoDB database name.",
    )
    parser.add_argument(
        "--transactions-collection",
        default="transactions",
        help="MongoDB collection that contains raw transactions.",
    )
    parser.add_argument(
        "--output-collection",
        default="subscriber_profile",
        help="MongoDB collection to write per-subscriber profiles to.",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the output collection before writing results.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of transaction documents to read (for testing).",
    )
    return parser


def _fetch_transactions(client: MongoClient, database: str, collection: str, limit: int = None) -> List[dict]:
    db = client[database]
    coll = db[collection]
    cursor = coll.find({})
    if limit is not None:
        cursor = cursor.limit(limit)
    docs = list(cursor)
    return docs


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure subscriber_id exists (some sources use csubscriber_id)
    if "subscriber_id" not in df.columns and "subscriber_id" in df.columns:
        df["subscriber_id"] = df["subscriber_id"]

    # Parse datetimes
    for col in ("record_opening_time", "record_closing_time", "load_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numeric conversions
    for col in ("cc_input_octets_bytes", "cc_output_octets_bytes", "cc_total_octets_bytes", "usage_mb"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Compute download/upload MB from octets if present
    df["download_mb"] = None
    df["upload_mb"] = None
    if "cc_input_octets_bytes" in df.columns:
        df["download_mb"] = df["cc_input_octets_bytes"].fillna(0) / (1024 * 1024)
    if "cc_output_octets_bytes" in df.columns:
        df["upload_mb"] = df["cc_output_octets_bytes"].fillna(0) / (1024 * 1024)

    # total_usage_mb: prefer explicit `usage_mb` field, otherwise sum download+upload
    df["total_usage_mb"] = None
    if "usage_mb" in df.columns:
        df["total_usage_mb"] = df["usage_mb"]
    else:
        df["total_usage_mb"] = df["download_mb"].fillna(0) + df["upload_mb"].fillna(0)

    # Ensure subscriber identifier exists
    if "subscriber_id" not in df.columns:
        raise RuntimeError("No subscriber_id or subscriber_id field found in transactions.")

    return df


def build_profiles(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("subscriber_id")

    result = grouped.agg(
        total_download_mb=("download_mb", "sum"),
        total_upload_mb=("upload_mb", "sum"),
        total_usage_mb=("total_usage_mb", "sum"),
        avg_usage_mb=("total_usage_mb", "mean"),
        max_usage_mb=("total_usage_mb", "max"),
        Number_of_sessions=("record_opening_time", "count"),
    )

    # Fill NaN with zeros for numeric fields
    numeric_cols = ["total_download_mb", "total_upload_mb", "total_usage_mb", "avg_usage_mb", "max_usage_mb", "Number_of_sessions"]
    for col in numeric_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    result = result.reset_index()
    return result


def save_profiles(client: MongoClient, database: str, collection: str, df: pd.DataFrame, drop: bool = False) -> int:
    db = client[database]
    coll = db[collection]
    if drop:
        coll.drop()

    operations = []
    for _, row in df.iterrows():
        doc = {
            "subscriber_id": row["subscriber_id"],
            "total_download_mb": float(row["total_download_mb"]),
            "total_upload_mb": float(row["total_upload_mb"]),
            "total_usage_mb": float(row["total_usage_mb"]),
            "avg_usage_mb": float(row["avg_usage_mb"]),
            "max_usage_mb": float(row["max_usage_mb"]),
            "Number_of_sessions": int(row["Number_of_sessions"]),
        }
        operations.append(ReplaceOne({"subscriber_id": doc["subscriber_id"]}, doc, upsert=True))

    if operations:
        result = coll.bulk_write(operations)
        # bulk_write does not return inserted count easily for upserts; return matched+upserted
        return (result.matched_count or 0) + (result.upserted_count or 0)
    return 0


def main() -> None:
    parser = _parse_args()
    args = parser.parse_args()

    client = MongoClient("mongodb://localhost:27017")
    docs = _fetch_transactions(client, args.database, args.transactions_collection, args.limit)
    if not docs:
        print("No transactions found; aborting.")
        return

    df = pd.DataFrame(docs)
    df = _normalize_df(df)
    profiles = build_profiles(df)

    written = save_profiles(client, args.database, args.output_collection, profiles, drop=args.drop)
    print(f"Wrote {len(profiles)} subscriber profiles (operations applied: {written}) to collection '{args.output_collection}'.")


if __name__ == "__main__":
    main()
