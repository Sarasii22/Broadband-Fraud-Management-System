from app.db.mongo import MongoTransactionRepository


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, _value):
        return self

    def limit(self, _value):
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents
        self.last_query = None

    def find(self, query):
        self.last_query = query
        return FakeCursor(self.documents)


def test_fetch_transactions_applies_customer_filter(monkeypatch):
    fake_collection = FakeCollection([{"_id": "1", "subscriber_id": "SUB-1"}])
    monkeypatch.setattr("app.db.mongo.get_collection", lambda collection_name=None: fake_collection)

    repository = MongoTransactionRepository()
    documents = repository.fetch_transactions(collection_name="transactions", customer_id="CUST-1", skip=2, limit=5)

    assert fake_collection.last_query == {"$or": [{"customer_id": "CUST-1"}, {"subscriber_id": "CUST-1"}]}
    assert len(documents) == 1
    assert documents[0]["subscriber_id"] == "SUB-1"