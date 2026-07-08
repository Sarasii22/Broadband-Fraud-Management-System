from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
)
from app.core.logging import setup_logging
from app.services.batch import score_batch_documents, to_storage_documents
from app.services.ml import MODEL_VERSION, get_model
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

    # Make sure the predictions collection has the indexes it needs
    # before any time-range queries hit it.
    MongoPredictionRepository().ensure_indexes()
    logger.info("Ensured indexes on fraud_predictions collection")


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

        # --- Automatic storage ---
        # Every scored batch is persisted with a timestamp so it can be
        # queried later by time period via /stats/by-time.
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


@app.post("/stats/by-time", response_model=TimeRangeStatsResponse)
def stats_by_time(request: TimeRangeStatsRequest):
    prediction_repository = MongoPredictionRepository()

    try:
        result = prediction_repository.fetch_stats_by_time_range(
            start_time=request.start_time,
            end_time=request.end_time,
            collection_name=request.collection_name,
        )
    except Exception as e:
        logger.exception("Time-range stats query failed")
        raise HTTPException(status_code=500, detail=f"Stats query failed: {e}")

    summary_counts = {item["_id"]: item["count"] for item in result.get("summary", [])}
    fraud_count = summary_counts.get(True, 0)
    normal_count = summary_counts.get(False, 0)
    total = fraud_count + normal_count

    fraud_pct = round((fraud_count / total) * 100, 2) if total else 0.0
    normal_pct = round((normal_count / total) * 100, 2) if total else 0.0

    records = [FraudRecordSummary(**r) for r in result.get("records", [])]

    return TimeRangeStatsResponse(
        start_time=request.start_time,
        end_time=request.end_time,
        total_records=total,
        fraud_count=fraud_count,
        normal_count=normal_count,
        fraud_percentage=fraud_pct,
        normal_percentage=normal_pct,
        records=records,
    )