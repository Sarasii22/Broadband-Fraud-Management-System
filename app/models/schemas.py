from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TransactionRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id", description="MongoDB document id")
    subscriber_id: str = Field(
        ...,
        validation_alias=AliasChoices("subscriber_id", "customer_id"),
        description="Unique subscriber identifier",
    )
    record_opening_time: Optional[datetime] = Field(default=None, description="Session start time")
    record_closing_time: Optional[datetime] = Field(default=None, description="Session end time")
    cc_total_octets_bytes: Optional[int] = Field(default=None, ge=0, description="Total octets in bytes")
    cc_input_octets_bytes: Optional[int] = Field(default=None, ge=0, description="Input octets in bytes")
    cc_output_octets_bytes: Optional[int] = Field(default=None, ge=0, description="Output octets in bytes")
    load_date: Optional[datetime] = Field(default=None, description="Ingestion timestamp")

    usage_mb: Optional[float] = Field(default=None, ge=0, description="Legacy data usage in MB")
    avg_usage_mb: Optional[float] = Field(default=None, ge=0, description="Legacy 30-day average usage in MB")
    device_age_days: Optional[int] = Field(default=None, ge=0, description="Days since this device was first seen")
    num_devices_30d: Optional[int] = Field(default=None, ge=0, description="Distinct devices used in last 30 days")
    failed_payments_7d: Optional[int] = Field(default=None, ge=0, description="Failed payment attempts in last 7 days")
    account_age_days: Optional[int] = Field(default=None, ge=0, description="Days since account was created")
    login_hour: Optional[int] = Field(default=None, ge=0, le=23, description="Hour of day (0-23) of this login/event")
    distance_from_usual_km: Optional[float] = Field(default=None, ge=0, description="Distance from subscriber's usual location")
    mac_address: Optional[str] = Field(default=None, description="Device MAC address")

    model_config = ConfigDict(populate_by_name=True)

    def to_scoring_payload(self) -> Dict[str, Any]:
        event_time = self.record_opening_time or self.load_date or self.record_closing_time or datetime.now(timezone.utc)
        raw_octets = self.cc_total_octets_bytes
        input_octets = self.cc_input_octets_bytes or 0
        output_octets = self.cc_output_octets_bytes or 0
        if raw_octets is None or raw_octets <= 0:
            raw_octets = input_octets + output_octets

        usage_mb = self.usage_mb if self.usage_mb is not None else round(raw_octets / (1024 * 1024), 4)

        return {
            "customer_id": self.subscriber_id,
            "usage_mb": usage_mb,
            "avg_usage_mb": self.avg_usage_mb if self.avg_usage_mb is not None else usage_mb,
            "device_age_days": self.device_age_days if self.device_age_days is not None else 0,
            "num_devices_30d": self.num_devices_30d if self.num_devices_30d is not None else 1,
            "failed_payments_7d": self.failed_payments_7d if self.failed_payments_7d is not None else 0,
            "account_age_days": self.account_age_days if self.account_age_days is not None else 0,
            "login_hour": self.login_hour if self.login_hour is not None else event_time.hour,
            "distance_from_usual_km": self.distance_from_usual_km if self.distance_from_usual_km is not None else 0.0,
            "mac_address": self.mac_address if self.mac_address is not None else self.subscriber_id,
        }


class BatchPredictionRequest(BaseModel):
    collection_name: Optional[str] = Field(
        default=None,
        description="MongoDB collection to read transactions from. Uses the configured default when omitted.",
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Optional customer filter for the stored dataset.",
    )
    skip: int = Field(default=0, ge=0, description="Number of matching documents to skip before scoring.")
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of matching documents to score. Omit to score all matching records.",
    )


class BatchPredictionItem(BaseModel):
    document_id: Optional[str] = None
    customer_id: str
    is_fraud: bool
    rule_score: float
    ml_score: float
    final_score: float
    decision: str
    triggered_rules: List[str]
    model_version: str


class BatchPredictionSummary(BaseModel):
    total_records: int
    fraud_count: int
    not_fraud_count: int
    average_rule_score: float
    average_ml_score: float
    average_final_score: float


class BatchPredictionResponse(BaseModel):
    collection_name: str
    matched_count: int
    predictions: List[BatchPredictionItem]
    summary: BatchPredictionSummary


class TimeRangeStatsRequest(BaseModel):
    start_time: datetime = Field(
        ..., description="Start of the period (inclusive), e.g. 2026-07-01T00:00:00"
    )
    end_time: datetime = Field(
        ..., description="End of the period (inclusive), e.g. 2026-07-08T23:59:59"
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Predictions collection to query. Uses the default (fraud_predictions) when omitted.",
    )


class FraudRecordSummary(BaseModel):
    customer_id: str
    is_fraud: bool
    decision: str
    final_score: float
    rule_score: float
    ml_score: float
    triggered_rules: List[str]
    created_at: datetime


class TriggeredRuleStat(BaseModel):
    """
    How often a single rule fired within the requested time period, and
    what fraction of those firings turned out to be actual fraud.
    """
    rule: str
    total: int
    fraud_count: int
    fraud_percentage: float


class TimeRangeStatsResponse(BaseModel):
    start_time: datetime
    end_time: datetime
    total_records: int
    fraud_count: int
    normal_count: int
    fraud_percentage: float
    normal_percentage: float
    records: List[FraudRecordSummary]
    rule_breakdown: List[TriggeredRuleStat] = Field(default_factory=list)


class CustomerLookupResponse(BaseModel):
    customer_id: str
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)