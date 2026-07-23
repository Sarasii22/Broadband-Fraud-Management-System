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


CONFIG_PATH_YAML = os.path.join(
    os.path.dirname(__file__),
    "..",
    "config",
    "rules.yaml"
)
CONFIG_PATH_YML = os.path.join(
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

    config_file = CONFIG_PATH_YAML if os.path.exists(CONFIG_PATH_YAML) else CONFIG_PATH_YML

    with open(config_file, "r") as file:
        return yaml.safe_load(file)


def rule_based_score(data: dict) -> Tuple[float, List[str], bool]:
    """
    Calculate rule-based fraud score.

    Returns
    -------
    normalized_score : float
    triggered_rules : list
    hard_block : bool
    """

    cfg = load_rules()
    score = 0
    triggered_rules = []
    hard_block = False

    # Compute derived upload_ratio if not present
    eval_data = dict(data)
    if "upload_ratio" not in eval_data:
        dl = float(eval_data.get("total_download_mb", 0) or 0)
        ul = float(eval_data.get("total_upload_mb", 0) or 0)
        eval_data["upload_ratio"] = (ul / dl * 100) if dl > 0 else 0.0

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
        if rule_name in cfg:
            rule = cfg[rule_name]
            feature = rule["feature"]
            val = float(eval_data.get(feature, 0) or 0)
            if val > rule["upper_limit"]:
                score += rule["points"]
                triggered_rules.append(rule_name)
                if rule.get("hard_block"):
                    hard_block = True

    # -------------------------------
    # Rule 08
    # -------------------------------

    if "rule_08" in cfg:
        rule = cfg["rule_08"]
        algos = int(eval_data.get("algorithms_flagged", 0) or 0)
        if algos >= rule["minimum_algorithms"]:
            score += rule["points"]
            triggered_rules.append("rule_08")
            if rule.get("hard_block"):
                hard_block = True

    # -------------------------------
    # Normalize Score
    # -------------------------------

    normalized_score = min(
        score / cfg.get("max_raw_score", 100),
        1.0
    )

    return normalized_score, triggered_rules, hard_block