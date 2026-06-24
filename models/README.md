# Models Workspace

This directory is the ignored local workspace for model packages and delivery
bundles. Git tracks only this README plus `.gitkeep` placeholders; weights,
ONNX files, OM files, and compressed delivery artifacts stay local.

## Directory Roles

| Path | Role |
| --- | --- |
| `edgeeye-detector-v1/` | Four-class detector baseline package for `insulator_normal`, `insulator_surface_damage`, `transformer_normal`, and `transformer_surface_damage`. |
| `edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/` | Current recall-first two-class insulator candidate package. This is not a drop-in replacement for the four-class baseline. |
| `artifacts/` | Compressed handoff bundles, checksums, and temporary model artifacts generated from package directories. |

The earlier `edgeeye-insulator-v1-opt30-yolov8s-adamw/` local package has been
removed from this workspace. Its metrics, hashes, and reproduction commands are
kept in `dataset/docs/edgeeye-insulator-v1-optimization-report.md`.

## Expected Package Shape

Each model package should keep the files needed to reproduce handoff behavior:

```text
<model-package>/
  best.pt
  best.onnx
  classes.json
  label.names
  preprocess-v1.json
  expected-output-v1.json
```

Optional package-local files such as `validation-metrics.json` are allowed when
they capture evaluation output not yet promoted into `dataset/docs/`.

## Cleanup Policy

- Do not commit large model artifacts. Keep them ignored under `models/` or
  `models/artifacts/`.
- Do not replace `edgeeye-detector-v1/` with an insulator-only candidate without
  an explicit promotion decision and contract update.
- Before deleting a non-empty package, confirm that its metrics, hashes, and
  promotion status are recorded under `dataset/docs/`.
- Delivery archives under `models/artifacts/` should keep a matching checksum
  file and should be regenerated from the package directory when stale.
- Empty directories, failed ad hoc exports, and duplicate temporary artifacts
  can be removed after confirming they are not referenced by docs or handoff
  scripts.

## Related Docs

- `training/README.md`
- `dataset/docs/edgeeye-detector-v1-baseline-report.md`
- `dataset/docs/edgeeye-insulator-v1-optimization-report.md`
- `dataset/docs/edgeeye-insulator-v1-domain-r1-report.md`
- `model-deploy/README.md`
