"""
Rule-based Fraud Scoring Service

This module applies configurable fraud detection rules defined in
config/rules.yml.

Each rule has:
    - feature
    - upper_limit
    - points

The module returns:
    - normalized rule score (0-1)
    - triggered rules
"""

import os
from typing import Tuple, List, Dict

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "config",
    "rules.yml"
)


def load_rules() -> Dict:
    """
    Load rule configuration from YAML file.
    """

    if yaml is None:
        raise RuntimeError(
            "PyYAML is not installed. Install requirements.txt."
        )

    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def rule_based_score(data: dict) -> Tuple[float, List[str]]:
    """
    Calculate rule-based fraud score.

    Parameters
    ----------
    data : dict

        Example:

        {
            "total_usage_mb": 900,
            "total_download_mb": 600,
            "total_upload_mb": 300,
            "avg_usage_mb": 120,
            "max_usage_mb": 450,
            "Number_of_sessions": 25,
            "upload_ratio": 6.8,
            "algorithms_flagged": 4
        }

    Returns
    -------
    normalized_score : float
        Rule score between 0 and 1

    triggered_rules : list
        List of triggered rule names
    """

    cfg = load_rules()

    score = 0

    triggered_rules = []

    # -------------------------------
    # Rule 01 - Rule 07
    # -------------------------------

    for rule_name in [
        "rule_01",
        "rule_02",
        "rule_03",
        "rule_04",
        "rule_05",
        "rule_06",
        "rule_07"
    ]:

        rule = cfg[rule_name]

        feature = rule["feature"]

        if data[feature] > rule["upper_limit"]:

            score += rule["points"]

            triggered_rules.append(rule_name)

    # -------------------------------
    # Rule 08
    # -------------------------------

    if "rule_08" in cfg:

        rule = cfg["rule_08"]

        if data["algorithms_flagged"] >= rule["minimum_algorithms"]:

            score += rule["points"]

            triggered_rules.append("rule_08")

    # -------------------------------
    # Normalize Score
    # -------------------------------

    normalized_score = min(
        score / cfg["max_raw_score"],
        1.0
    )

    return normalized_score, triggered_rules