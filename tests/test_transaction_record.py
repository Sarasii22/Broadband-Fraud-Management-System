from app.models.schemas import TransactionRecord


def test_transaction_record_derives_scoring_payload_from_raw_table():
    record = TransactionRecord.model_validate(
        {
            "subscriber_id": "SUB_365EECB8",
            "record_opening_time": "2026-05-16T11:00:00",
            "record_closing_time": "2026-05-16T10:00:00",
            "cc_total_octets_bytes": 0,
            "cc_input_octets_bytes": 8094,
            "cc_output_octets_bytes": 0,
            "load_date": "2026-05-17T05:04:50",
        }
    )

    payload = record.to_scoring_payload()

    assert payload["customer_id"] == "SUB_365EECB8"
    assert payload["usage_mb"] == 0.0077
    assert payload["avg_usage_mb"] == 0.0077
    assert payload["login_hour"] == 11
    assert payload["mac_address"] == "SUB_365EECB8"