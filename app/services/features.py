"""
Shared feature engineering for subscriber-level anomaly detection.

This module is used by both

1. Offline model training
2. Online prediction

Keeping preprocessing here guarantees that the prediction data is
prepared exactly the same way as the training data.
"""

from typing import Any

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None


# Features used by the Isolation Forest model
FEATURE_COLUMNS = [
    "total_download_mb",
    "total_upload_mb",
    "total_usage_mb",
    "avg_usage_mb",
    "max_usage_mb",
    "Number_of_sessions",
]


def build_features(data: dict) -> Any:
    """
    Convert a subscriber JSON record into the DataFrame expected
    by the scaler and Isolation Forest model.

    Parameters
    ----------
    data : dict

    Example
    -------
    {
        "subscriber_id":"SUB_001",
        "total_download_mb":465,
        "total_upload_mb":29,
        "total_usage_mb":495,
        "avg_usage_mb":61,
        "max_usage_mb":116,
        "Number_of_sessions":8
    }

    Returns
    -------
    pandas.DataFrame
    """

    if pd is None:
        raise RuntimeError(
            "Pandas is not installed. Install requirements.txt first."
        )

    row = {
        "subscriber_id": data["subscriber_id"],
        "total_download_mb": float(data["total_download_mb"]),
        "total_upload_mb": float(data["total_upload_mb"]),
        "total_usage_mb": float(data["total_usage_mb"]),
        "avg_usage_mb": float(data["avg_usage_mb"]),
        "max_usage_mb": float(data["max_usage_mb"]),
        "Number_of_sessions": int(data["Number_of_sessions"]),
    }

    df = pd.DataFrame([row])

    # subscriber_id is NOT a model feature.
    # It is only used as an identifier.
    df = df.set_index("subscriber_id")

    return df[FEATURE_COLUMNS]