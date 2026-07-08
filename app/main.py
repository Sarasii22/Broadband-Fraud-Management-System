from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from app.db.mongo import (
    DEFAULT_MONGODB_COLLECTION,
    MongoTransactionRepository,
    MongoPredictionRepository,
)
from app.models.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    TimeRangeStatsRequest,
    TimeRangeStatsResponse,
    FraudRecordSummary,
    TriggeredRuleStat,
)
from app.core.logging import setup_logging
from app.services.batch import score_batch_documents, to_storage_documents
from app.services.ml import MODEL_VERSION, get_model
from app.services.report import build_pdf_report
from app.services.auto_scorer import start_auto_scorer, stop_auto_scorer
import os

logger = setup_logging()

app = FastAPI(
    title="Broadband Fraud Batch API",
    description="MongoDB-backed batch fraud scoring for broadband accounts",
    version="1.0.0",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def load_model_on_startup():
    get_model()
    logger.info("XGBoost model loaded, version=%s", MODEL_VERSION)

    MongoPredictionRepository().ensure_indexes()
    logger.info("Ensured indexes on fraud_predictions collection")

    # Start the background poller: it watches `transactions` for any
    # documents that don't have a corresponding fraud_predictions entry
    # yet, scores them, and saves the result — automatically, without
    # needing a manual POST /predict call.
    start_auto_scorer()


@app.on_event("shutdown")
def stop_background_workers():
    stop_auto_scorer()


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=BatchPredictionResponse)
def predict_batch(request: BatchPredictionRequest):
    repository = MongoTransactionRepository()
    prediction_repository = MongoPredictionRepository()
    collection_name = request.collection_name or DEFAULT_MONGODB_COLLECTION

    try:
        documents = repository.fetch_transactions(
            collection_name=request.collection_name,
            customer_id=request.customer_id,
            skip=request.skip,
            limit=request.limit,
        )
        predictions, summary = score_batch_documents(documents)

        storage_docs = to_storage_documents(predictions)
        saved_count = prediction_repository.save_predictions(storage_docs)
        logger.info("Saved %d scored predictions to fraud_predictions", saved_count)

    except Exception as e:
        logger.exception("Batch prediction failed for collection=%s", collection_name)
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {e}")

    return BatchPredictionResponse(
        collection_name=collection_name,
        matched_count=len(predictions),
        predictions=predictions,
        summary=summary,
    )


def _compute_stats(request: TimeRangeStatsRequest) -> TimeRangeStatsResponse:
    """
    Shared logic used by both the JSON stats endpoint and the PDF report
    endpoint, so the two never drift out of sync with each other.
    """
    prediction_repository = MongoPredictionRepository()

    result = prediction_repository.fetch_stats_by_time_range(
        start_time=request.start_time,
        end_time=request.end_time,
        collection_name=request.collection_name,
    )

    summary_counts = {item["_id"]: item["count"] for item in result.get("summary", [])}
    fraud_count = summary_counts.get(True, 0)
    normal_count = summary_counts.get(False, 0)
    total = fraud_count + normal_count

    fraud_pct = round((fraud_count / total) * 100, 2) if total else 0.0
    normal_pct = round((normal_count / total) * 100, 2) if total else 0.0

    records = [FraudRecordSummary(**r) for r in result.get("records", [])]

    rule_breakdown = [
        TriggeredRuleStat(
            rule=r["rule"],
            total=r["total"],
            fraud_count=r["fraud_count"],
            fraud_percentage=round(r["fraud_percentage"], 2),
        )
        for r in result.get("rule_breakdown", [])
    ]

    return TimeRangeStatsResponse(
        start_time=request.start_time,
        end_time=request.end_time,
        total_records=total,
        fraud_count=fraud_count,
        normal_count=normal_count,
        fraud_percentage=fraud_pct,
        normal_percentage=normal_pct,
        records=records,
        rule_breakdown=rule_breakdown,
    )


@app.post("/stats/by-time", response_model=TimeRangeStatsResponse)
def stats_by_time(request: TimeRangeStatsRequest):
    try:
        return _compute_stats(request)
    except Exception as e:
        logger.exception("Time-range stats query failed")
        raise HTTPException(status_code=500, detail=f"Stats query failed: {e}")


@app.post("/stats/by-time/report")
def stats_by_time_report(request: TimeRangeStatsRequest):
    """
    Same data as /stats/by-time, but rendered as a downloadable PDF,
    including a bar chart of triggered rules vs fraud percentage.
    """
    try:
        stats = _compute_stats(request)

        pdf_bytes = build_pdf_report(
            start_time=stats.start_time,
            end_time=stats.end_time,
            total_records=stats.total_records,
            fraud_count=stats.fraud_count,
            normal_count=stats.normal_count,
            fraud_percentage=stats.fraud_percentage,
            normal_percentage=stats.normal_percentage,
            records=[r.model_dump() for r in stats.records],
            rule_breakdown=[r.model_dump() for r in stats.rule_breakdown],
        )
    except Exception as e:
        logger.exception("PDF report generation failed")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    filename = f"fraud_report_{stats.start_time.date()}_{stats.end_time.date()}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )