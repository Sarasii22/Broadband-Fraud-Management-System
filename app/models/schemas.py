from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class TransactionRecord(BaseModel):
    """
    Subscriber profile model.

    Example MongoDB document:

    {
        "_id": "6a619e8e4c68c3159bc70dca",
        "subscriber_id": "SUB_2922DC01",
        "total_download_mb": 562.61,
        "total_upload_mb": 44.52,
        "total_usage_mb": 607.14,
        "avg_usage_mb": 67.46,
        "max_usage_mb": 120.76,
        "Number_of_sessions": 9
    }
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


    model_config = ConfigDict(
        populate_by_name=True
    )


    def to_scoring_payload(self) -> Dict[str, Any]:
        """
        Convert subscriber profile into ML model input format.
        """

        total_usage = (
            self.total_usage_mb
            if self.total_usage_mb is not None
            else 0
        )

        avg_usage = (
            self.avg_usage_mb
            if self.avg_usage_mb is not None
            else total_usage
        )

        sessions = (
            self.Number_of_sessions
            if self.Number_of_sessions is not None
            else 0
        )

        return {
            "subscriber_id": self.subscriber_id,
            "total_download_mb": self.total_download_mb or 0,
            "total_upload_mb": self.total_upload_mb or 0,
            "total_usage_mb": total_usage,
            "avg_usage_mb": avg_usage,
            "max_usage_mb": self.max_usage_mb or 0,
            "Number_of_sessions": sessions,

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
    label: int
    rule_score: float
    fraud_score: float
    raw_score: float
    final_score: float
    decision: str
    triggered_rules: List[str]
    model_version: str


class BatchPredictionSummary(BaseModel):
    total_records: int
    fraud_count: int
    normal_count: int
    average_rule_score: float
    average_fraud_score: float
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
    subscriber_id: str
    label: int
    decision: str
    final_score: float
    rule_score: float
    fraud_score: float
    raw_score: float
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


class SubscriberLookupResponse(BaseModel):
    subscriber_id: str
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)