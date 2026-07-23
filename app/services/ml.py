"""
Isolation Forest ML Scoring Service

This module:

1. Loads the trained Isolation Forest model.
2. Loads the StandardScaler used during training.
3. Loads the score scaler used to normalize anomaly scores.
4. Builds features from incoming subscriber data.
5. Predicts whether the subscriber is anomalous.
6. Returns a normalized fraud score.
"""

import os
import joblib
import numpy as np
from typing import Any

from app.services.features import build_features

# ==========================================================
# Base Project Directory
#
# Current file:
# app/services/ml.py
#
# Move up:
# services -> app -> Project Root
# ==========================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# ==========================================================
# MODEL PATHS
#
# Change these filenames ONLY if your files have different names.
# ==========================================================

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "isolation_forest_model.pkl"
)

FEATURE_SCALER_PATH = os.path.join(
    BASE_DIR,
    "scalers",
    "standard_scaler.pkl"
)

SCORE_SCALER_PATH = os.path.join(
    BASE_DIR,
    "scalers",
    "score_scaler.pkl"
)

MODEL_VERSION = "IsolationForest_v1"

# ==========================================================
# Lazy Loaded Objects
# ==========================================================

_model = None
_feature_scaler = None
_score_scaler = None

# ==========================================================
# Load Isolation Forest
# ==========================================================

def get_model() -> Any:
    global _model

    if _model is None:
        _model = joblib.load(MODEL_PATH)

    return _model


# ==========================================================
# Load Feature Scaler
# ==========================================================

def get_feature_scaler() -> Any:
    global _feature_scaler

    if _feature_scaler is None:
        _feature_scaler = joblib.load(FEATURE_SCALER_PATH)

    return _feature_scaler


# ==========================================================
# Load Score Scaler
# ==========================================================

def get_score_scaler() -> Any:
    global _score_scaler

    if _score_scaler is None:
        _score_scaler = joblib.load(SCORE_SCALER_PATH)

    return _score_scaler


# ==========================================================
# ML Prediction
# ==========================================================

def ml_score(data: dict) -> dict:
    """
    Predict anomaly using Isolation Forest.

    Returns
    -------
    {
        "label": 0 or 1,
        "fraud_score": float,
        "raw_score": float
    }

    label:
        0 = Normal
        1 = Anomaly
    """

    model = get_model()
    feature_scaler = get_feature_scaler()
    score_scaler = get_score_scaler()

    # ------------------------------------------
    # Build feature dataframe
    # ------------------------------------------

    X = build_features(data)

    # ------------------------------------------
    # Scale features
    # ------------------------------------------

    X_scaled = feature_scaler.transform(X)

    # ------------------------------------------
    # Predict
    #
    # Isolation Forest returns:
    #
    #  1  -> Normal
    # -1  -> Anomaly
    # ------------------------------------------

    prediction = model.predict(X_scaled)[0]

    label = 1 if prediction == -1 else 0

    # ------------------------------------------
    # Raw anomaly score
    # ------------------------------------------

    raw_score = model.score_samples(X_scaled)[0]

    # ------------------------------------------
    # Normalize score
    # ------------------------------------------

    fraud_score = 1 - score_scaler.transform(
        np.array([[raw_score]])
    ).ravel()[0]

    fraud_score = float(np.clip(fraud_score, 0, 1))

    return {
        "label": label,
        "fraud_score": fraud_score,
        "raw_score": float(raw_score),
        "model_version": MODEL_VERSION
    }