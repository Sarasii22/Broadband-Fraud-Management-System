from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class TransactionRecord(BaseModel):
    """
    Subscriber profile / raw transaction model.
    """

    id: Optional[str] = Field(
        default=None,
        alias="_id",
        description="MongoDB document id"
    )

    subscriber_id: str = Field(
        ...,
        validation_alias=AliasChoices("subscriber_id", "subscriber_id"),
        description="Unique subscriber identifier"
    )

    total_download_mb: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total downloaded data in MB"
    )

    total_upload_mb: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total uploaded data in MB"
    )

    total_usage_mb: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total internet usage in MB"
    )

    avg_usage_mb: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average usage per session in MB"
    )

    max_usage_mb: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum usage in a single session"
    )

    Number_of_sessions: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of sessions"
    )

    # Raw transaction table fields
    record_opening_time: Optional[Any] = Field(default=None)
    record_closing_time: Optional[Any] = Field(default=None)
    cc_total_octets_bytes: Optional[int] = Field(default=None)
    cc_input_octets_bytes: Optional[int] = Field(default=None)
    cc_output_octets_bytes: Optional[int] = Field(default=None)
    load_date: Optional[Any] = Field(default=None)
    mac_address: Optional[str] = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        protected_namespaces=()
    )

    def to_scoring_payload(self) -> Dict[str, Any]:
        """
        Convert subscriber profile or raw transaction record into ML model input format.
        """
        raw_sum = (self.cc_input_octets_bytes or 0) + (self.cc_output_octets_bytes or 0)
        has_octets = (
            self.cc_total_octets_bytes is not None
            or self.cc_input_octets_bytes is not None
            or self.cc_output_octets_bytes is not None
        )
        usage_bytes = max(self.cc_total_octets_bytes or 0, raw_sum) if has_octets else None

        computed_mb = round(usage_bytes / (1024 * 1024), 4) if usage_bytes is not None else None

        total_download = (
            self.total_download_mb
            if self.total_download_mb is not None
            else (round((self.cc_input_octets_bytes or 0) / (1024 * 1024), 4) if self.cc_input_octets_bytes is not None else 0.0)
        )

        total_upload = (
            self.total_upload_mb
            if self.total_upload_mb is not None
            else (round((self.cc_output_octets_bytes or 0) / (1024 * 1024), 4) if self.cc_output_octets_bytes is not None else 0.0)
        )

        total_usage = (
            self.total_usage_mb
            if self.total_usage_mb is not None
            else (computed_mb if computed_mb is not None else (total_download + total_upload))
        )

        avg_usage = (
            self.avg_usage_mb
            if self.avg_usage_mb is not None
            else total_usage
        )

        max_usage = (
            self.max_usage_mb
            if self.max_usage_mb is not None
            else total_usage
        )

        sessions = (
            self.Number_of_sessions
            if self.Number_of_sessions is not None
            else 1
        )

        login_hour = 0
        if self.record_opening_time:
            if isinstance(self.record_opening_time, datetime):
                login_hour = self.record_opening_time.hour
            elif isinstance(self.record_opening_time, str):
                try:
                    dt = datetime.fromisoformat(self.record_opening_time)
                    login_hour = dt.hour
                except ValueError:
                    login_hour = 0

        mac_addr = self.mac_address or self.subscriber_id

        return {
            "subscriber_id": self.subscriber_id,
            "total_download_mb": total_download,
            "total_upload_mb": total_upload,
            "total_usage_mb": total_usage,
            "usage_mb": total_usage,
            "avg_usage_mb": avg_usage,
            "max_usage_mb": max_usage,
            "Number_of_sessions": sessions,
            "login_hour": login_hour,
            "mac_address": mac_addr,
        }

class BatchPredictionRequest(BaseModel):
    collection_name: Optional[str] = Field(
        default=None,
        description="MongoDB collection to read transactions from. Uses the configured default when omitted.",
    )
    subscriber_id: Optional[str] = Field(
        default=None,
        description="Optional subscriber filter for the stored dataset.",
    )
    skip: int = Field(default=0, ge=0, description="Number of matching documents to skip before scoring.")
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of matching documents to score. Omit to score all matching records.",
    )

class BatchPredictionItem(BaseModel):
    document_id: Optional[str] = None
    subscriber_id: str
    is_fraud: bool = False
    label: int = 0
    rule_score: float
    fraud_score: float = 0.0
    ml_score: float = 0.0
    raw_score: float = 0.0
    final_score: float
    decision: str
    triggered_rules: List[str] = Field(default_factory=list)
    model_version: str = "v1.0.0"

    model_config = ConfigDict(protected_namespaces=())

class BatchPredictionSummary(BaseModel):
    total_records: int
    fraud_count: int
    normal_count: int = 0
    not_fraud_count: int = 0
    average_rule_score: float
    average_fraud_score: float = 0.0
    average_ml_score: float = 0.0
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
    subscriber_id: str = "UNKNOWN"
    is_fraud: bool = False
    label: int = 0
    decision: str = "ALLOW"
    final_score: float = 0.0
    rule_score: float = 0.0
    fraud_score: float = 0.0
    ml_score: float = 0.0
    raw_score: float = 0.0
    triggered_rules: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(protected_namespaces=())


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


class SubscriberLookupResponse(BaseModel):
    subscriber_id: str
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)