from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class TransactionRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id", description="MongoDB document id")
    customer_id: str = Field(..., description="Unique customer identifier")
    usage_mb: float = Field(..., ge=0, description="Data usage in this session/day (MB)")
    avg_usage_mb: float = Field(..., ge=0, description="Customer's 30-day average usage (MB)")
    device_age_days: int = Field(..., ge=0, description="Days since this device was first seen")
    num_devices_30d: int = Field(..., ge=0, description="Distinct devices used in last 30 days")
    failed_payments_7d: int = Field(..., ge=0, description="Failed payment attempts in last 7 days")
    account_age_days: int = Field(..., ge=0, description="Days since account was created")
    login_hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23) of this login/event")
    distance_from_usual_km: float = Field(..., ge=0, description="Distance from customer's usual location")
    mac_address: str = Field(..., description="Device MAC address")

    class Config:
        populate_by_name = True


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


class TimeRangeStatsResponse(BaseModel):
    start_time: datetime
    end_time: datetime
    total_records: int
    fraud_count: int
    normal_count: int
    fraud_percentage: float
    normal_percentage: float
    records: List[FraudRecordSummary]