from __future__ import annotations

from pathlib import Path

import yaml

from alfworld_eval.env import split_to_train_eval


def test_textworld_config_is_text_only() -> None:
    root = Path(__file__).resolve().parents[1]
    with (root / "configs" / "textworld.yaml").open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    assert config["env"]["type"] == "AlfredTWEnv"
    assert config["general"]["use_cuda"] is False
    assert config["general"]["training_method"] == "dqn"
    assert config["dataset"]["eval_id_data_path"].endswith("/valid_seen")
    assert config["dataset"]["eval_ood_data_path"].endswith("/valid_unseen")


def test_split_mapping_matches_alfworld_protocol() -> None:
    assert split_to_train_eval("train") == "train"
    assert split_to_train_eval("valid_seen") == "eval_in_distribution"
    assert split_to_train_eval("valid_unseen") == "eval_out_of_distribution"
