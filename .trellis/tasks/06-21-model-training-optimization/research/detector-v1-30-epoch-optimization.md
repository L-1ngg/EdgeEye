# Research: detector-v1 30-epoch training optimization

- Query: practical optimization options for improving the existing EdgeEye `edgeeye-detector-v1` YOLOv8n baseline, capped at 30 epochs, with safe dataset-folder cleanup
- Scope: mixed
- Date: 2026-06-21

## Findings

### Files found

- `dataset/docs/edgeeye-detector-v1-baseline-report.md` — first complete 50-epoch YOLOv8n baseline report, metrics, handoff hashes, known risks.
- `training/README.md` — local training flow from dataset.yaml to `best.pt`, ONNX export, expected-output generation, ignored outputs.
- `.trellis/spec/training/index.md` — training-layer checklist and quality gates.
- `.trellis/spec/training/model-training-handoff.md` — detector-v1 training/export/handoff contract and expected output shape.
- `.trellis/spec/training/dataset-preparation.md` — detector-v1 class order, source mappings, generated dataset contract.
- `dataset/README.md` — dataset workspace roles and current local inventory.
- `dataset/docs/edgeeye-detector-v1-report.md` — conversion counts, class distribution by split, included source counts, remaining dataset risks.
- `dataset/docs/sources.md` — source datasets, local paths, source labels, download/extraction status.
- `training/train.py` — current training wrapper and exposed CLI arguments.
- `training/prepare_dataset.py` — dataset conversion, output reset behavior, source archive lookup paths, split generation.
- `training/validate_dataset.py` — dataset.yaml/classes/labels consistency and YOLO label validation.
- `training/runs/edgeeye-detector-v1/args.yaml` — baseline resolved Ultralytics arguments and default augmentation/hyperparameters.
- `training/runs/edgeeye-detector-v1/results.csv` — per-epoch training metrics for the 50-epoch baseline.
- `dataset/processed/edgeeye-detector-v1/dataset.yaml` — generated YOLO dataset config with train/val/test and class names.
- `dataset/processed/edgeeye-detector-v1/manifest.json` — generated conversion manifest with sources, split counts, class counts, excluded classes, inventory hashes.
- `.gitignore` — ignored dataset/model/run artifact policy.
- `.trellis/tasks/06-21-model-training-optimization/prd.md` — current task requirements and open questions.
- `.trellis/tasks/06-21-model-training-optimization/design.md` — current planning draft for candidate output strategy and initial recipe.
- `.trellis/tasks/06-21-model-training-optimization/implement.md` — current planning draft for implementation and validation sequence.

### Baseline evidence

- Baseline environment used Ultralytics `8.4.70`, PyTorch `2.12.1+cu130`, CUDA, and an RTX 4060 Laptop GPU (`dataset/docs/edgeeye-detector-v1-baseline-report.md:27`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:33`).
- Baseline dataset validation passed with 10,411 images and 145,382 boxes across train/val/test (`dataset/docs/edgeeye-detector-v1-baseline-report.md:49`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:56`).
- Class imbalance is extreme: `insulator_normal` has 135,814 boxes, `insulator_surface_damage` has 6,727, `transformer_normal` has 2,754, and `transformer_surface_damage` has only 87 (`dataset/docs/edgeeye-detector-v1-baseline-report.md:58`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:65`).
- The baseline command trained `yolov8n.pt` for 50 epochs at `imgsz=640`, `batch=8`, `device=0` (`dataset/docs/edgeeye-detector-v1-baseline-report.md:99`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:111`).
- The best mAP50 row was epoch 30: precision `0.83609`, recall `0.67325`, mAP50 `0.76917`, mAP50-95 `0.40178` (`dataset/docs/edgeeye-detector-v1-baseline-report.md:128`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:134`).
- The best mAP50-95 row was epoch 27: precision `0.79043`, recall `0.66237`, mAP50 `0.73967`, mAP50-95 `0.40565` (`dataset/docs/edgeeye-detector-v1-baseline-report.md:136`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:142`).
- Independent validation of the copied `best.pt` reported all-class precision `0.79045`, recall `0.66170`, mAP50 `0.73991`, and mAP50-95 `0.40442` (`dataset/docs/edgeeye-detector-v1-baseline-report.md:144`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:153`).
- The weakest important class is `insulator_surface_damage`: recall `0.46319`, mAP50 `0.63551`, mAP50-95 `0.27248` (`dataset/docs/edgeeye-detector-v1-baseline-report.md:147`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:153`).
- `transformer_surface_damage` validation metrics are volatile because the validation split has only 12 boxes; the report already flags this risk (`dataset/docs/edgeeye-detector-v1-baseline-report.md:223`-`dataset/docs/edgeeye-detector-v1-baseline-report.md:231`).
- Baseline `args.yaml` confirms default `patience=100`, `optimizer=auto`, `seed=0`, `deterministic=true`, `close_mosaic=10`, `mosaic=1.0`, `mixup=0.0`, `cutmix=0.0`, `copy_paste=0.0`, `lr0=0.01`, `lrf=0.01`, and `cls=0.5` (`training/runs/edgeeye-detector-v1/args.yaml:7`-`training/runs/edgeeye-detector-v1/args.yaml:27`, `training/runs/edgeeye-detector-v1/args.yaml:74`-`training/runs/edgeeye-detector-v1/args.yaml:108`).

### Code patterns

- Current `training/train.py` only exposes `--data`, `--model`, `--epochs`, `--imgsz`, `--batch`, `--device`, `--workers`, `--project`, `--name`, and `--copy-best-to` (`training/train.py:16`-`training/train.py:40`).
- The wrapper passes only those values into `model.train()` and does not expose Ultralytics tuning args such as `patience`, `optimizer`, `lr0`, `lrf`, `cos_lr`, `mosaic`, `mixup`, `copy_paste`, `close_mosaic`, `freeze`, `cache`, `seed`, or `split` (`training/train.py:46`-`training/train.py:60`).
- The training wrapper copies the best checkpoint to a stable path after training (`training/train.py:60`-`training/train.py:66`).
- The generated `dataset.yaml` uses the expected Ultralytics YOLO format with `train`, `val`, `test`, `nc=4`, and the fixed detector-v1 class names (`dataset/processed/edgeeye-detector-v1/dataset.yaml:1`-`dataset/processed/edgeeye-detector-v1/dataset.yaml:10`).
- `prepare_dataset.py --overwrite` deletes and recreates the processed output directory when it is non-empty, so processed-data cleanup should be deliberate and scripted, not manual (`training/prepare_dataset.py:153`-`training/prepare_dataset.py:160`).
- `prepare_dataset.py` currently searches for raw archives at top-level dataset paths such as `dataset/24060960.zip`, `dataset/Transformer Station Detection.v1i.yolov8.zip`, and `dataset/insulator-defect-detection-DatasetNinja.tar`; moving archives into a cleaner folder requires script changes or compatibility lookup paths (`training/prepare_dataset.py:357`-`training/prepare_dataset.py:363`, `training/prepare_dataset.py:431`-`training/prepare_dataset.py:437`, `training/prepare_dataset.py:595`-`training/prepare_dataset.py:605`).
- Substation split generation is deterministic by sorted eligible label order and an 80/10/10 split, which means reorganization should preserve source paths or rerun validation/reporting (`training/prepare_dataset.py:516`-`training/prepare_dataset.py:570`).
- `validate_dataset.py` checks class metadata alignment and normalized YOLO boxes before training (`training/validate_dataset.py:121`-`training/validate_dataset.py:162`).
- Large local artifacts are ignored: `dataset/raw/`, `dataset/staging/`, `dataset/processed/`, `dataset/downloads/`, `dataset/cache/`, `dataset/*.zip`, `dataset/*.tar`, `training/runs/`, `runs/`, `models/`, `*.pt`, `*.onnx`, and `*.om` (`.gitignore:24`-`.gitignore:39`).

### Top 5 realistic optimization levers for the next 30-epoch run

1. **Move from `yolov8n.pt` to `yolov8s.pt` while keeping `imgsz=640`.**
   - Why: the baseline underfits or misses fault boxes, and YOLOv8s has materially more capacity than YOLOv8n while remaining far smaller than `m/l/x`. Ultralytics' YOLOv8 table lists COCO mAP50-95 `37.3` for `yolov8n` and `44.9` for `yolov8s`, with params increasing from `3.2M` to `11.2M`.
   - Repo fit: directly supported by `training/train.py --model`.
   - Risk: slower training/inference and larger export; Atlas speed should be checked before promotion.

2. **Add script pass-through for bounded hyperparameters and run one deliberate recipe, not a wide search.**
   - Why: baseline already peaked around epochs 27-30, so the next run should improve convergence inside the same cap. Useful first-pass knobs are `optimizer=AdamW`, `cos_lr=True`, lower `lr0`, `lrf`, `patience`, `close_mosaic`, and a fixed seed.
   - Repo fit: Ultralytics supports these args, but current `training/train.py` does not expose them.
   - Risk: too many simultaneous changes make attribution hard. Keep one recipe and compare directly to the baseline.

3. **Tune augmentation for fault recall without overwhelming rare labels.**
   - Why: baseline used `mosaic=1.0`, `close_mosaic=10`, and no `mixup`/`copy_paste`. Mosaic can help small objects and context variety, but excessive composition can make training harder; light `mixup` can improve robustness but can also add label noise.
   - Repo fit: requires `training/train.py` pass-through or using `yolo` CLI directly.
   - Recommendation: start with moderate augmentation rather than aggressive augmentation: `mosaic=0.75`, `close_mosaic=8`, `mixup=0.05`, `copy_paste=0.0`. If results worsen, fall back to baseline augmentation (`mosaic=1.0`, `close_mosaic=10`, no mixup).
   - Risk: for only 87 total transformer-damage boxes, augmentation may not replace real data.

4. **Fix the data imbalance through sampling or candidate-data construction rather than loss weighting first.**
   - Why: `insulator_normal` dominates 135,814 of 145,382 boxes, while both fault classes are much smaller. The first lever should be a reproducible balanced candidate dataset or source-aware sampling because it preserves ordinary Ultralytics checkpoints.
   - Repo fit: requires dataset/conversion script changes. Current converter writes all kept data and does not sample by class.
   - Recommendation: do not apply destructive cleanup or delete normal examples. If the first `yolov8s`/hyperparameter run fails, create a candidate dataset that caps or down-samples excessive normal-only substation examples, oversamples/copies fault-heavy source images into train only, and keeps the existing val/test splits for comparison.
   - Risk: changing the dataset invalidates direct comparison unless the split and manifest are documented.

5. **Treat `imgsz=768` as a second-pass experiment, not the first run.**
   - Why: larger image size can help small/long-distance objects and is directly supported by current scripts, but it changes compute cost and the ONNX/preprocess contract if promoted.
   - Repo fit: `training/train.py --imgsz` and `export_onnx.py --imgsz` support this directly.
   - Recommendation: keep the first optimization run at `640` to preserve Atlas handoff shape. Try `768` only if the 640 candidate cannot improve fault recall and the team accepts a new export/preprocess version.
   - Risk: slower training, possible RTX 4060 laptop memory pressure, and incompatible `[1,3,640,640]` handoff unless versioned.

### Current script support vs required changes

| Lever / setting | Current `training/train.py` support | Needs script changes? | Notes |
| --- | --- | --- | --- |
| 30-epoch cap | Yes: `--epochs 30` | No | Default `patience=100` means no early stop before 30 unless exposed. |
| Model size | Yes: `--model yolov8s.pt` | No | Also supports `yolov8n.pt`, `yolov8m.pt`, local `.pt`, or yaml paths. |
| Image size | Yes: `--imgsz 640` or `768` | No | Export script also supports `--imgsz`; handoff currently documents 640. |
| Batch | Yes: `--batch 8` | No | Arg is `int`; `--batch -1` should pass Ultralytics auto-batch but should be smoke-tested before relying on it. |
| Device/workers | Yes | No | Current baseline used `device=0`, `workers=4`. |
| Project/name/candidate checkpoint path | Yes | No | Use candidate names/paths to avoid overwriting baseline. |
| Patience/early stopping | No | Yes, unless using raw `yolo` CLI | Add pass-through if the project wants wrapper-only training. |
| Optimizer / learning rate / cosine LR | No | Yes, unless using raw `yolo` CLI | Recommended small pass-through set. |
| Augmentation values | No | Yes, unless using raw `yolo` CLI | Baseline defaults are visible in `args.yaml`. |
| Cache | No | Yes, unless using raw `yolo` CLI | May speed I/O but dataset is 43G; RAM/disk impact must be checked. |
| Freeze / transfer-learning schedule | No | Yes, unless using raw `yolo` CLI | Keep unfrozen for first `yolov8s` run; consider `freeze=10` only if overfitting appears. |
| Class-balanced sampling | No | Yes | Requires conversion/sampling design. |
| Class-weighted loss | No | Yes, custom trainer/model | Highest checkpoint-loading risk; do not use in first pass. |
| Alternative checkpoint fitness such as recall | No | Yes, custom trainer | Useful later if product prioritizes recall over mAP50-95. |

### Recommended first 30-epoch recipe

Use a candidate directory and preserve the existing baseline handoff until the candidate wins.

If the training wrapper is left unchanged, use the lowest-risk command:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8s.pt \
  --epochs 30 \
  --imgsz 640 \
  --batch 8 \
  --device 0 \
  --workers 4 \
  --name edgeeye-detector-v1-opt30-yolov8s \
  --copy-best-to ../models/edgeeye-detector-v1-opt30-yolov8s/best.pt
```

Preferred recipe if `training/train.py` is extended with pass-through args before training:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8s.pt \
  --epochs 30 \
  --imgsz 640 \
  --batch 8 \
  --device 0 \
  --workers 4 \
  --name edgeeye-detector-v1-opt30-yolov8s-adamw \
  --copy-best-to ../models/edgeeye-detector-v1-opt30-yolov8s-adamw/best.pt \
  --patience 12 \
  --optimizer AdamW \
  --lr0 0.003 \
  --lrf 0.01 \
  --cos-lr \
  --mosaic 0.75 \
  --close-mosaic 8 \
  --mixup 0.05 \
  --copy-paste 0.0 \
  --seed 0 \
  --deterministic
```

Recipe assumptions:

- Hardware: same local RTX 4060 Laptop GPU with CUDA. Start with `batch=8`; if out-of-memory, retry the same recipe with `batch=4` before changing anything else.
- Model size: `yolov8s.pt` first. It is a practical capacity bump from `yolov8n.pt` without jumping to `yolov8m/l/x`.
- Image size: keep `640` for the first candidate so ONNX output remains compatible with the documented `[1,3,640,640]` handoff.
- Evaluation split: train validates on the generated `val` split; after selecting the best candidate, generate expected outputs from `test` like the baseline flow.
- Early stopping: `patience=12` is enough inside a 30-epoch cap to stop if the candidate clearly stalls, but it will not prematurely stop on ordinary short-term noise.
- Augmentation: reduce mosaic from `1.0` to `0.75`, close it for the final 8 epochs, add only light `mixup=0.05`, and leave copy-paste off.
- Do not change class order, label mapping, ONNX opset, or inference thresholds in this first training run.

### Safe dataset folder cleanup / organization plan

Current tracked docs define the intended dataset layout as:

```text
dataset/
  raw/
  staging/
  processed/
  docs/
```

`dataset/README.md` also says large raw, staging, processed, download, and cache directories are ignored, and only lightweight metadata/source notes/conversion scripts/manifests should be committed (`dataset/README.md:3`-`dataset/README.md:7`, `dataset/README.md:21`-`dataset/README.md:29`).

Safe non-destructive plan:

1. Inventory before any cleanup:
   - record `find dataset -maxdepth 3 -type d`
   - record top-level archive files and sizes/hashes from `manifest.json`
   - record existing `models/`, `training/runs/`, and `runs/` as generated/ignored artifacts
2. Keep raw source directories and top-level archives in place for now:
   - `dataset/raw/aerial-power-infrastructure-detection-train/`
   - `dataset/raw/insulator-defect-detection/`
   - `dataset/raw/transformer-station-detection/`
   - `dataset/raw/substation-equipment-15class/`
   - `dataset/24060960.zip`
   - `dataset/Transformer Station Detection.v1i.yolov8.zip`
   - `dataset/insulator-defect-detection-DatasetNinja.tar`
3. Treat `dataset/processed/edgeeye-detector-v1/` as generated. Do not hand-edit it. Regenerate only with `prepare_dataset.py --overwrite` after a reviewed dataset-change decision.
4. Keep empty `dataset/staging/`, `dataset/downloads/`, and `dataset/cache/` unless the team wants empty-directory removal. Removing empty ignored directories is safe but low value; keeping them documents intended roles.
5. If better archive organization is desired, implement it as a later script-backed change:
   - introduce `dataset/downloads/archives/`
   - update `prepare_dataset.py` to search both old and new archive paths
   - copy archives first, validate hashes and full conversion
   - only then ask for approval to remove duplicate top-level archive copies
6. Do not delete the previous baseline runs or `models/edgeeye-detector-v1/` during cleanup. Candidate runs should use versioned paths until promoted.

### Success criteria against the previous baseline

Use the independent validation table in the baseline report as the reference, not only the training `results.csv`.

Minimum promotion criteria:

- 30-epoch cap honored: no run exceeds `epochs=30`.
- Same evaluation basis: compare against the generated `val` split in `dataset/processed/edgeeye-detector-v1/dataset.yaml`.
- Handoff compatibility: candidate exports to ONNX with opset 11 and the expected 640 input shape before promotion.
- All-class mAP50-95 improves from `0.40442` to at least `0.414` absolute, or stays within `0.005` of baseline while materially improving fault recall.
- All-class mAP50 does not regress below `0.725` and ideally improves above `0.73991`.
- `insulator_surface_damage` recall improves from `0.46319` to at least `0.55` target, with an acceptable floor around `0.52` only if precision and mAP50-95 also improve.
- `insulator_surface_damage` mAP50-95 improves from `0.27248` to at least `0.30` target.
- Normal-class performance guardrail: no normal class should lose more than about `0.03` absolute mAP50-95 without an explicit recall-focused decision.
- `transformer_surface_damage` metrics should be reported but not over-weighted because validation has only 12 boxes. Guardrail only: avoid collapse below roughly `0.50` recall or `0.35` mAP50-95 unless visual inspection proves the class is mislabeled or statistically unstable.
- Precision/recall trade-off must be explicit: a candidate that gains recall by flooding false positives is not a promotion candidate unless product requirements change.

### External references

- Ultralytics configuration docs: https://docs.ultralytics.com/usage/cfg/
  - Used for official meanings of `epochs`, `patience`, `batch`, `imgsz`, `cache`, `device`, `project`, `name`, `optimizer`, augmentation knobs, and performance-tuning categories.
- Ultralytics data augmentation docs: https://docs.ultralytics.com/guides/yolo-data-augmentation/
  - Used for official behavior of `mosaic`, `close_mosaic`, and `mixup`.
- Ultralytics YOLOv8 docs: https://docs.ultralytics.com/models/yolov8/
  - Used for official YOLOv8 model variants and the n/s/m/l/x size-performance trade-off table.
- Ultralytics detection dataset docs: https://docs.ultralytics.com/datasets/detect/
  - Used for official YOLO dataset YAML and label-format expectations.
- Ultralytics hyperparameter tuning docs: https://docs.ultralytics.com/guides/hyperparameter-tuning/
  - Used for the recommendation to set a tuning budget and identify metrics before experiments.
- Ultralytics fine-tuning docs: https://docs.ultralytics.com/guides/finetuning-guide/
  - Used for pretrained-weight fine-tuning assumptions and freezing trade-offs.
- Ultralytics custom trainer docs: https://docs.ultralytics.com/guides/custom-trainer/
  - Used to classify class-weighted loss and custom checkpoint fitness as script/custom-trainer changes, not first-pass wrapper args.

### Related specs

- `.trellis/spec/training/index.md`
  - Requires reading dataset and handoff specs before changing training scripts or generated metadata.
  - Requires keeping generated large artifacts under ignored dataset/model/run paths.
- `.trellis/spec/training/model-training-handoff.md`
  - Defines smoke/full training command shapes, ONNX opset 11, 640 input shape, expected-output fixture contract, and ignored model package rules.
- `.trellis/spec/training/dataset-preparation.md`
  - Defines fixed detector-v1 class order, source mappings, excluded source classes, validation behavior, and generated dataset rules.

## Caveats / Not Found

- I did not modify code, dataset files, model files, training runs, or docs outside this research note.
- I did not run a new training job, ONNX export, or dataset conversion for this research.
- I did not inspect images visually; recommendations are based on metrics, manifests, script behavior, and documented source mappings.
- I did not find built-in class weighting or class-aware sampling support in the current project scripts. Ultralytics supports custom trainers for this class of change, but that is a higher-risk second pass.
- Web references are official Ultralytics docs, but some pages now use newer YOLO family names in examples. The settings cited here are still Ultralytics training concepts relevant to this repo's installed `ultralytics>=8.3,<9` package, but exact behavior should be checked with a smoke run after script changes.
- The `transformer_surface_damage` validation class has only 12 boxes, so any single-run metric movement for that class is weak evidence.
