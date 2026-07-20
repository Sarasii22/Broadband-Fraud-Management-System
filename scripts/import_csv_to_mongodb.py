from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
from pymongo import MongoClient


def _parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Import transaction rows into MongoDB.")
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).resolve().parents[1] / "training" / "synthetic_broadband_fraud_data.csv"),
        help="Path to the CSV file to import.",
    )
    parser.add_argument(
        "--database",
        default="fraud_api",
        help="MongoDB database name.",
    )
    parser.add_argument(
        "--collection",
        default="transactions",
        help="MongoDB collection name.",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Delete existing documents before inserting the CSV rows.",
    )
    return parser


def _normalize_transaction_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [column.strip() for column in df.columns]

    rename_map = {
        "subscriber id": "subscriber_id",
        "record opening time": "record_opening_time",
        "record closing time": "record_closing_time",
        "cc total octets bytes": "cc_total_octets_bytes",
        "cc input octets bytes": "cc_input_octets_bytes",
        "cc output octets bytes": "cc_output_octets_bytes",
        "load date": "load_date",
    }
    df = df.rename(columns={column: rename_map.get(column.lower(), column) for column in df.columns})

    for column in ("record_opening_time", "record_closing_time", "load_date"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
            df[column] = df[column].apply(lambda value: value.to_pydatetime() if pd.notnull(value) else None)

    if "subscriber_id" in df.columns and "customer_id" not in df.columns:
        df["customer_id"] = df["subscriber_id"]
    elif "customer_id" in df.columns and "subscriber_id" not in df.columns:
        df["subscriber_id"] = df["customer_id"]

    numeric_columns = [
        "cc_total_octets_bytes",
        "cc_input_octets_bytes",
        "cc_output_octets_bytes",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.where(pd.notnull(df), None)


def main() -> None:
    parser = _parse_args()
    args = parser.parse_args()

    client = MongoClient("mongodb://localhost:27017")
    db = client[args.database]
    collection = db[args.collection]

    df = pd.read_csv(args.csv)
    df = _normalize_transaction_columns(df)
    records = df.to_dict(orient="records")

    if args.drop:
        collection.delete_many({})

    if records:
        collection.insert_many(records)

    print(f"Inserted {len(records)} records into MongoDB collection '{args.collection}'.")


if __name__ == "__main__":
	main()