from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import BatchPredictionItem
from app.services.batch import build_batch_summary


def test_build_batch_summary_counts_and_averages():
    predictions = [
        BatchPredictionItem(
            document_id="1",
            subscriber_id="SUB-1",
            is_fraud=False,
            rule_score=0.2,
            ml_score=0.4,
            final_score=0.3,
            decision="ALLOW",
            triggered_rules=[],
            model_version="v1.0.0",
        ),
        BatchPredictionItem(
            document_id="2",
            subscriber_id="SUB-2",
            is_fraud=True,
            rule_score=0.8,
            ml_score=0.9,
            final_score=0.85,
            decision="BLOCK",
            triggered_rules=["usage_spike"],
            model_version="v1.0.0",
        ),
        BatchPredictionItem(
            document_id="3",
            subscriber_id="SUB-3",
            is_fraud=True,
            rule_score=0.5,
            ml_score=0.6,
            final_score=0.55,
            decision="REVIEW",
            triggered_rules=["many_devices"],
            model_version="v1.0.0",
        ),
    ]

    summary = build_batch_summary(predictions)

    assert summary.total_records == 3
    assert summary.fraud_count == 2
    assert summary.not_fraud_count == 1
    assert summary.average_rule_score == 0.5
    assert summary.average_ml_score == 0.6333
    assert summary.average_final_score == 0.5667


def test_batch_endpoint_returns_summary_and_predictions(monkeypatch):
    fake_documents = [{"_id": "mongo-1", "subscriber_id": "SUB-100"}]

    def fake_fetch_transactions(self, collection_name=None, subscriber_id=None, skip=0, limit=None):
        return fake_documents

    monkeypatch.setattr("app.main.get_model", lambda: None)
    monkeypatch.setattr("app.main.MongoTransactionRepository.fetch_transactions", fake_fetch_transactions)
    monkeypatch.setattr(
        "app.main.score_batch_documents",
        lambda documents: (
            [
                BatchPredictionItem(
                    document_id="mongo-1",
                    subscriber_id="SUB-100",
                    is_fraud=False,
                    rule_score=0.1,
                    ml_score=0.2,
                    final_score=0.18,
                    decision="ALLOW",
                    triggered_rules=[],
                    model_version="v1.0.0",
                )
            ],
            build_batch_summary(
                [
                    BatchPredictionItem(
                        document_id="mongo-1",
                        subscriber_id="SUB-100",
                        is_fraud=False,
                        rule_score=0.1,
                        ml_score=0.2,
                        final_score=0.18,
                        decision="ALLOW",
                        triggered_rules=[],
                        model_version="v1.0.0",
                    )
                ]
            ),
        ),
    )

    client = TestClient(app)
    response = client.post("/predict", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["collection_name"] == "transactions"
    assert payload["matched_count"] == 1
    assert payload["summary"]["total_records"] == 1
    assert payload["summary"]["not_fraud_count"] == 1
    assert payload["predictions"][0]["subscriber_id"] == "SUB-100"
    assert payload["predictions"][0]["is_fraud"] is False