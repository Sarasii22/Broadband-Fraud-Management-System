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
    # Extreme Fraud Subscriber
    # Should trigger many rules
    # ===============================

    {
        "subscriber_id": "SUB_FRAUD_001",
        "record_opening_time": datetime(2026, 7, 20, 10, 0, 0),
        "record_closing_time": datetime(2026, 7, 20, 18, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 900_000_000,
        "cc_output_octets_bytes": 500_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_FRAUD_001",
        "record_opening_time": datetime(2026, 7, 21, 10, 0, 0),
        "record_closing_time": datetime(2026, 7, 21, 20, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 800_000_000,
        "cc_output_octets_bytes": 700_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },


    # ===============================
    # Heavy Download User
    # Rule 01,02,05
    # ===============================

    {
        "subscriber_id": "SUB_HEAVY_001",
        "record_opening_time": datetime(2026, 7, 22, 9, 0, 0),
        "record_closing_time": datetime(2026, 7, 22, 15, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 700_000_000,
        "cc_output_octets_bytes": 50_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },


    {
        "subscriber_id": "SUB_HEAVY_001",
        "record_opening_time": datetime(2026, 7, 23, 9, 0, 0),
        "record_closing_time": datetime(2026, 7, 23, 15, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 600_000_000,
        "cc_output_octets_bytes": 40_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },


    # ===============================
    # Upload Abuse User
    # Rule 03 and Rule 07
    # ===============================

    {
        "subscriber_id": "SUB_UPLOAD_001",
        "record_opening_time": datetime(2026, 7, 22, 22, 0, 0),
        "record_closing_time": datetime(2026, 7, 23, 2, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 20_000_000,
        "cc_output_octets_bytes": 300_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },


    # ===============================
    # Normal Subscriber
    # No rules triggered
    # ===============================

    {
        "subscriber_id": "SUB_NORMAL_001",
        "record_opening_time": datetime(2026, 7, 23, 12, 0, 0),
        "record_closing_time": datetime(2026, 7, 23, 14, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 50_000_000,
        "cc_output_octets_bytes": 5_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },


    # ===============================
    # Another Normal Subscriber
    # ===============================

    {
        "subscriber_id": "SUB_NORMAL_002",
        "record_opening_time": datetime(2026, 7, 23, 15, 0, 0),
        "record_closing_time": datetime(2026, 7, 23, 16, 0, 0),
        "cc_total_octets_bytes": 0,
        "cc_input_octets_bytes": 30_000_000,
        "cc_output_octets_bytes": 2_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    }
]

result = collection.insert_many(sample_records)
print(f"Inserted {len(result.inserted_ids)} sample transactions.")
print("Subscriber IDs added:", [r["subscriber_id"] for r in sample_records])