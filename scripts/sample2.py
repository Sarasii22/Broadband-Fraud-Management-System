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


    {
        "subscriber_id": "SUB_TEST_101",
        "record_opening_time": datetime(2026, 7, 23, 8, 30),
        "record_closing_time": datetime(2026, 7, 23, 18, 45),
        "cc_total_octets_bytes": 1_550_000_000,
        "cc_input_octets_bytes": 980_000_000,
        "cc_output_octets_bytes": 570_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_101",
        "record_opening_time": datetime(2026, 7, 24, 9, 0),
        "record_closing_time": datetime(2026, 7, 24, 20, 15),
        "cc_total_octets_bytes": 1_420_000_000,
        "cc_input_octets_bytes": 850_000_000,
        "cc_output_octets_bytes": 570_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_102",
        "record_opening_time": datetime(2026, 7, 23, 10, 0),
        "record_closing_time": datetime(2026, 7, 23, 16, 30),
        "cc_total_octets_bytes": 920_000_000,
        "cc_input_octets_bytes": 760_000_000,
        "cc_output_octets_bytes": 160_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_102",
        "record_opening_time": datetime(2026, 7, 24, 9, 30),
        "record_closing_time": datetime(2026, 7, 24, 14, 30),
        "cc_total_octets_bytes": 810_000_000,
        "cc_input_octets_bytes": 670_000_000,
        "cc_output_octets_bytes": 140_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_103",
        "record_opening_time": datetime(2026, 7, 23, 20, 0),
        "record_closing_time": datetime(2026, 7, 24, 2, 30),
        "cc_total_octets_bytes": 430_000_000,
        "cc_input_octets_bytes": 40_000_000,
        "cc_output_octets_bytes": 390_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_104",
        "record_opening_time": datetime(2026, 7, 23, 11, 15),
        "record_closing_time": datetime(2026, 7, 23, 13, 45),
        "cc_total_octets_bytes": 95_000_000,
        "cc_input_octets_bytes": 82_000_000,
        "cc_output_octets_bytes": 13_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    },

    {
        "subscriber_id": "SUB_TEST_105",
        "record_opening_time": datetime(2026, 7, 24, 15, 0),
        "record_closing_time": datetime(2026, 7, 24, 16, 10),
        "cc_total_octets_bytes": 48_000_000,
        "cc_input_octets_bytes": 40_000_000,
        "cc_output_octets_bytes": 8_000_000,
        "load_date": datetime(2026, 7, 24, 5, 4, 50),
    }

]

result = collection.insert_many(sample_records)
print(f"Inserted {len(result.inserted_ids)} sample transactions.")
print("Subscriber IDs added:", [r["subscriber_id"] for r in sample_records])