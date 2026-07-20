import os

import numpy as np
import pandas as pd

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "synthetic_broadband_fraud_data.csv")
DEFAULT_OPENING_TIME = pd.Timestamp("2026-05-16 11:00:00")
DEFAULT_CLOSING_TIME = pd.Timestamp("2026-05-16 10:00:00")
DEFAULT_LOAD_DATE = pd.Timestamp("2026-05-17 05:04:50")


def generate_broadband_synthetic_data(n_samples: int = 1000, fraud_rate: float = 0.5, seed: int = 42) -> pd.DataFrame:
    """
    Generate subscriber transaction rows in the new MongoDB table shape.

    Output columns:
    - subscriber_id
    - record_opening_time
    - record_closing_time
    - cc_total_octets_bytes
    - cc_input_octets_bytes
    - cc_output_octets_bytes
    - load_date
    """
    rng = np.random.default_rng(seed)

    base_ids = [f"SUB_{rng.integers(0, 16**8):08X}" for _ in range(n_samples)]

    input_octets = rng.integers(5_000, 120_000_000, size=n_samples)
    output_octets = rng.integers(0, 10_000_000, size=n_samples)

    # Keep the raw data aligned with the sample you provided: the total
    # octets field is zero and the actual usage sits in input/output.
    total_octets = np.zeros(n_samples, dtype=np.int64)

    df = pd.DataFrame(
        {
            "subscriber_id": base_ids,
            "record_opening_time": [DEFAULT_OPENING_TIME] * n_samples,
            "record_closing_time": [DEFAULT_CLOSING_TIME] * n_samples,
            "cc_total_octets_bytes": total_octets,
            "cc_input_octets_bytes": input_octets,
            "cc_output_octets_bytes": output_octets,
            "load_date": [DEFAULT_LOAD_DATE] * n_samples,
        }
    )

    # Optional stability tweak: keep the same deterministic row ordering
    # for a given seed, but still vary the values enough for testing.
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    print(f"\n=== Synthetic Transaction Data ===")
    print(f"Total samples: {len(df)}")
    print(f"Subscriber IDs: {df['subscriber_id'].iloc[0]} ... {df['subscriber_id'].iloc[-1]}")
    print(f"Input bytes range: {df['cc_input_octets_bytes'].min()} - {df['cc_input_octets_bytes'].max()}")
    print(f"Output bytes range: {df['cc_output_octets_bytes'].min()} - {df['cc_output_octets_bytes'].max()}")

    return df


if __name__ == "__main__":
    df = generate_broadband_synthetic_data()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} synthetic rows to {OUTPUT_PATH}")
