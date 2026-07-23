"""
Quick diagnostic: shows the most recently scored predictions and their
raw created_at (true UTC) timestamps, so you can compare them against
whatever start_time/end_time you typed into the dashboard.
"""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["fraud_api"]
collection = db["fraud_predictions"]

print("Most recent 5 predictions (created_at is TRUE UTC time):\n")
for doc in collection.find().sort("created_at", -1).limit(5):
    print(f"  subscriber_id={doc.get('subscriber_id'):<18} created_at (UTC) = {doc.get('created_at')}")