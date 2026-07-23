import sys
from pathlib import Path

# Add the project root (fraud_api) to Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.mongo import MongoTransactionRepository

repo = MongoTransactionRepository()

profiles = repo.fetch_transactions(limit=5)

print(f"Found {len(profiles)} profiles\n")

for profile in profiles:
    print(profile)