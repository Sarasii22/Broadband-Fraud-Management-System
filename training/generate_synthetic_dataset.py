import os

import numpy as np
import pandas as pd

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "synthetic_broadband_fraud_data.csv"
)

DEFAULT_OPENING_TIME = pd.Timestamp("2026-05-16 11:00:00")
DEFAULT_LOAD_DATE = pd.Timestamp("2026-05-17 05:04:50")


def generate_broadband_synthetic_data(
    n_subscribers: int = 100,
    min_sessions: int = 3,
    max_sessions: int = 10,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic broadband transaction data.

    Each subscriber will have multiple transaction records
    with different usage values and timestamps.

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

    # Generate unique subscriber IDs
    subscriber_ids = [
        f"SUB_{rng.integers(0, 16**8):08X}"
        for _ in range(n_subscribers)
    ]

    rows = []

    for subscriber in subscriber_ids:

        # Random number of sessions for each subscriber
        n_sessions = rng.integers(min_sessions, max_sessions + 1)

        for _ in range(n_sessions):

            # Random session start time
            opening_time = DEFAULT_OPENING_TIME + pd.Timedelta(
                minutes=int(rng.integers(0, 10080))  # Within one week
            )

            # Random session duration (1–180 minutes)
            duration = int(rng.integers(1, 181))

            closing_time = opening_time + pd.Timedelta(minutes=duration)

            # Random traffic
            input_octets = int(rng.integers(5_000, 120_000_000))
            output_octets = int(rng.integers(1_000, 10_000_000))

            total_octets = input_octets + output_octets

            rows.append(
                {
                    "subscriber_id": subscriber,
                    "record_opening_time": opening_time,
                    "record_closing_time": closing_time,
                    "cc_total_octets_bytes": total_octets,
                    "cc_input_octets_bytes": input_octets,
                    "cc_output_octets_bytes": output_octets,
                    "load_date": DEFAULT_LOAD_DATE,
                }
            )

    df = pd.DataFrame(rows)

    # Shuffle rows so transactions are not grouped together
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    print("\n========== Synthetic Dataset ==========")
    print(f"Subscribers           : {n_subscribers}")
    print(f"Transactions Generated: {len(df)}")
    print(
        f"Average Sessions/User : "
        f"{len(df) / n_subscribers:.2f}"
    )

    print("\nFirst 10 rows:")
    print(df.head(10))

    print("\nTransaction count per subscriber (first 10):")
    print(df["subscriber_id"].value_counts().head(10))

    return df


if __name__ == "__main__":

    df = generate_broadband_synthetic_data(
        n_subscribers=100,
        min_sessions=3,
        max_sessions=10,
        seed=42,
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(df)} transaction records")
    print(f"Output file: {OUTPUT_PATH}")