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
    # --- Obvious fraud patterns ---
    {
        "subscriber_id": "SUB-TEST-F001",
        "usage_mb": 18500.0,
        "avg_usage_mb": 1200.0,
        "device_age_days": 0,
        "num_devices_30d": 15,
        "failed_payments_7d": 4,
        "account_age_days": 2,
        "login_hour": 3,
        "distance_from_usual_km": 220.0,
        "mac_address": "FF:FF:FF:11:22:33",
    },
    {
        "subscriber_id": "SUB-TEST-F002",
        "usage_mb": 22000.0,
        "avg_usage_mb": 1500.0,
        "device_age_days": 1,
        "num_devices_30d": 12,
        "failed_payments_7d": 3,
        "account_age_days": 1,
        "login_hour": 2,
        "distance_from_usual_km": 300.0,
        "mac_address": "FF:FF:FF:44:55:66",
    },
    {
        # Hard-block: blacklisted MAC from your rules.yaml
        "subscriber_id": "SUB-TEST-F003",
        "usage_mb": 5000.0,
        "avg_usage_mb": 2000.0,
        "device_age_days": 10,
        "num_devices_30d": 4,
        "failed_payments_7d": 0,
        "account_age_days": 100,
        "login_hour": 14,
        "distance_from_usual_km": 5.0,
        "mac_address": "AA:BB:CC:DD:EE:FF",
    },

    # --- Obvious legitimate patterns ---
    {
        "subscriber_id": "SUB-TEST-L001",
        "usage_mb": 1400.0,
        "avg_usage_mb": 1450.0,
        "device_age_days": 400,
        "num_devices_30d": 4,
        "failed_payments_7d": 0,
        "account_age_days": 600,
        "login_hour": 19,
        "distance_from_usual_km": 2.0,
        "mac_address": "AA:BB:CC:10:20:30",
    },
    {
        "subscriber_id": "SUB-TEST-L002",
        "usage_mb": 1800.0,
        "avg_usage_mb": 1700.0,
        "device_age_days": 250,
        "num_devices_30d": 5,
        "failed_payments_7d": 0,
        "account_age_days": 900,
        "login_hour": 21,
        "distance_from_usual_km": 1.5,
        "mac_address": "AA:BB:CC:40:50:60",
    },

    # --- Borderline / REVIEW-ish pattern ---
    {
        "subscriber_id": "SUB-TEST-R001",
        "usage_mb": 6000.0,
        "avg_usage_mb": 2000.0,
        "device_age_days": 15,
        "num_devices_30d": 7,
        "failed_payments_7d": 1,
        "account_age_days": 20,
        "login_hour": 4,
        "distance_from_usual_km": 80.0,
        "mac_address": "AA:BB:CC:70:80:90",
    },

    {
        "subscriber_id": "SUB-TEST-R002",
        "usage_mb": 6000.0,
        "avg_usage_mb": 2000.0,
        "device_age_days": 5,
        "num_devices_30d": 17,
        "failed_payments_7d": 1,
        "account_age_days": 2,
        "login_hour": 4,
        "distance_from_usual_km": 80.0,
        "mac_address": "AA:BB:CC:70:80:90",
    },
]

result = collection.insert_many(sample_records)
print(f"Inserted {len(result.inserted_ids)} sample transactions.")
print("Subscriber IDs added:", [r["subscriber_id"] for r in sample_records])