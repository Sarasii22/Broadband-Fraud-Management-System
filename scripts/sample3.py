"""
Inserts a handful of hand-crafted sample transactions into the
`transactions` collection so you can test /predict and the dashboard
end-to-end. Run this whenever you want fresh test data.

Usage:
    python scripts/add_sample_transactions.py
"""

from datetime import datetime
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["fraud_api"]
collection = db["transactions"]

sample_records = [

    # ===============================
    # Subscriber 1 - Very High Usage
    # ===============================

    {
        "subscriber_id": "SUB_CASE_301",
        "record_opening_time": datetime(2026, 7, 23, 7, 30),
        "record_closing_time": datetime(2026, 7, 23, 22, 15),
        "cc_total_octets_bytes": 2_000_000_000,
        "cc_input_octets_bytes": 1_300_000_000,
        "cc_output_octets_bytes": 700_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_CASE_301",
        "record_opening_time": datetime(2026, 7, 24, 8, 0),
        "record_closing_time": datetime(2026, 7, 24, 21, 30),
        "cc_total_octets_bytes": 1_800_000_000,
        "cc_input_octets_bytes": 1_150_000_000,
        "cc_output_octets_bytes": 650_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    # ===============================
    # Subscriber 2 - Heavy Download
    # ===============================

    {
        "subscriber_id": "SUB_CASE_302",
        "record_opening_time": datetime(2026, 7, 23, 9, 15),
        "record_closing_time": datetime(2026, 7, 23, 17, 45),
        "cc_total_octets_bytes": 950_000_000,
        "cc_input_octets_bytes": 860_000_000,
        "cc_output_octets_bytes": 90_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_CASE_302",
        "record_opening_time": datetime(2026, 7, 24, 10, 0),
        "record_closing_time": datetime(2026, 7, 24, 16, 30),
        "cc_total_octets_bytes": 850_000_000,
        "cc_input_octets_bytes": 770_000_000,
        "cc_output_octets_bytes": 80_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    # ===============================
    # Subscriber 3 - Upload Heavy
    # ===============================

    {
        "subscriber_id": "SUB_CASE_303",
        "record_opening_time": datetime(2026, 7, 23, 20, 0),
        "record_closing_time": datetime(2026, 7, 24, 3, 30),
        "cc_total_octets_bytes": 650_000_000,
        "cc_input_octets_bytes": 90_000_000,
        "cc_output_octets_bytes": 560_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_CASE_303",
        "record_opening_time": datetime(2026, 7, 24, 21, 0),
        "record_closing_time": datetime(2026, 7, 24, 23, 45),
        "cc_total_octets_bytes": 720_000_000,
        "cc_input_octets_bytes": 110_000_000,
        "cc_output_octets_bytes": 610_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    # ===============================
    # Subscriber 4 - Medium Usage
    # ===============================

    {
        "subscriber_id": "SUB_CASE_304",
        "record_opening_time": datetime(2026, 7, 23, 13, 0),
        "record_closing_time": datetime(2026, 7, 23, 15, 0),
        "cc_total_octets_bytes": 220_000_000,
        "cc_input_octets_bytes": 180_000_000,
        "cc_output_octets_bytes": 40_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_CASE_304",
        "record_opening_time": datetime(2026, 7, 24, 11, 30),
        "record_closing_time": datetime(2026, 7, 24, 13, 15),
        "cc_total_octets_bytes": 240_000_000,
        "cc_input_octets_bytes": 190_000_000,
        "cc_output_octets_bytes": 50_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    # ===============================
    # Subscriber 5 - Normal User
    # ===============================

    {
        "subscriber_id": "SUB_CASE_305",
        "record_opening_time": datetime(2026, 7, 23, 18, 0),
        "record_closing_time": datetime(2026, 7, 23, 18, 50),
        "cc_total_octets_bytes": 60_000_000,
        "cc_input_octets_bytes": 48_000_000,
        "cc_output_octets_bytes": 12_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_CASE_305",
        "record_opening_time": datetime(2026, 7, 24, 19, 0),
        "record_closing_time": datetime(2026, 7, 24, 19, 45),
        "cc_total_octets_bytes": 55_000_000,
        "cc_input_octets_bytes": 43_000_000,
        "cc_output_octets_bytes": 12_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    }

]

result = collection.insert_many(sample_records)
print(f"Inserted {len(result.inserted_ids)} sample transactions.")
print("Subscriber IDs added:", [r["subscriber_id"] for r in sample_records])