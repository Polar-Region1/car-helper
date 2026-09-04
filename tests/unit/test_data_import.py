from collections import Counter

import pytest

from src.pipeline.data_import.import_data import load_and_validate_data, parse_args


def test_import_is_dry_run_by_default():
    args = parse_args([])
    assert args.apply is False
    assert args.replace is False


def test_replace_requires_apply_and_explicit_confirmation():
    with pytest.raises(SystemExit):
        parse_args(["--replace"])
    with pytest.raises(SystemExit):
        parse_args(["--apply", "--replace"])

    args = parse_args(["--apply", "--replace", "--confirm-replace"])
    assert args.apply is True
    assert args.replace is True


def test_batch_size_is_bounded():
    with pytest.raises(SystemExit):
        parse_args(["--batch-size", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--batch-size", "5001"])


def test_model_relationships_are_bound_to_stable_source_ids():
    bundle = load_and_validate_data()
    models_by_id = {model["_source_id"]: model for model in bundle.models}

    for relationship, model_field in (
        (bundle.series_models, "right"),
        (bundle.model_energy, "left"),
        (bundle.model_prices, "left"),
    ):
        assert relationship
        assert all(row["model_id"] in models_by_id for row in relationship)
        assert all(
            models_by_id[row["model_id"]]["车名"] == row[model_field]
            for row in relationship
        )

    name_counts = Counter(model["车名"] for model in bundle.models)
    duplicate_ids = {
        model["_source_id"] for model in bundle.models if name_counts[model["车名"]] > 1
    }
    assert len(duplicate_ids) > 1
    assert duplicate_ids.issubset({row["model_id"] for row in bundle.series_models})
