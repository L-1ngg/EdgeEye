# Training Development Guidelines

> Guidelines for the local YOLO training and dataset preparation layer.

## Current Stack

- Runtime: Python 3.12 through `uv`.
- Dataset format: Ultralytics YOLO train/val/test directories.
- Training package: `training/`.
- Dataset workspace: `dataset/`.

## Guidelines Index

| Guide | Description | Status |
| --- | --- | --- |
| [Dataset Preparation](./dataset-preparation.md) | Detector-v1 source mappings, generated dataset contracts, validation commands | Active |
| [Model Training Handoff](./model-training-handoff.md) | Detector-v1 training, ONNX export, expected-output generation, ignored handoff package | Active |

## Pre-Development Checklist

- Read `dataset-preparation.md` before changing `training/prepare_dataset.py`, dataset class mappings, generated metadata, or dataset docs.
- Read `model-training-handoff.md` before changing `training/train.py`, `training/export_onnx.py`, `training/generate_expected_output.py`, model output paths, or handoff package shape.
- Keep detector class order aligned across `dataset.yaml`, `classes.json`, `label.names`, and YOLO label files.
- Preserve ignored large artifacts under `dataset/raw/`, `dataset/processed/`, `training/runs/`, and `models/`.

## Quality Check

- Run `python -m py_compile` on changed training scripts.
- Run a smoke conversion with `uv run python prepare_dataset.py --limit-per-source 20 --overwrite`.
- Run a full conversion with `uv run python prepare_dataset.py --overwrite` when source mappings change.
- Validate with `uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml --classes ../dataset/processed/edgeeye-detector-v1/classes.json --labels ../dataset/processed/edgeeye-detector-v1/label.names`.
- For training/export changes, run `check_env.py`, dataset validation, a smoke training/export chain when feasible, and ONNX plus `expected-output-v1.json` validation.
- Update `dataset/README.md`, `dataset/docs/sources.md`, and `dataset/docs/edgeeye-detector-v1-report.md` when full conversion counts change.
- Update the baseline/handoff report when a full training run or exported model package changes.
