import json
import subprocess
from pathlib import Path

from app.core.config import settings
from app.services import edge_model as edge_model_module
from app.services.edge_model import EdgeModelInferenceService


def test_edge_model_service_parses_bridge_output(monkeypatch, tmp_path: Path) -> None:
    model_path = tmp_path / "model.om"
    script_path = tmp_path / "bridge.py"
    classes_path = tmp_path / "classes.json"
    preprocess_path = tmp_path / "preprocess.json"
    image_path = tmp_path / "frame.jpg"
    annotated_path = tmp_path / "annotated.jpg"
    for path in [model_path, script_path, classes_path, preprocess_path, image_path]:
        path.write_bytes(b"placeholder")

    monkeypatch.setattr(settings, "edge_model_enabled", True)
    monkeypatch.setattr(settings, "edge_model_python", "python3")
    monkeypatch.setattr(settings, "edge_model_script", str(script_path))
    monkeypatch.setattr(settings, "edge_model_path", str(model_path))
    monkeypatch.setattr(settings, "edge_model_classes_path", str(classes_path))
    monkeypatch.setattr(settings, "edge_model_preprocess_path", str(preprocess_path))
    monkeypatch.setattr(settings, "edge_model_output_shape", "1,6,8400")
    monkeypatch.setattr(settings, "edge_model_device_id", 0)
    monkeypatch.setattr(settings, "edge_model_timeout_seconds", 15.0)

    def fake_run(command, **kwargs):
        assert command[0].endswith("python3")
        assert command[1] == str(script_path)
        assert str(model_path) in command
        assert str(classes_path) in command
        assert str(preprocess_path) in command
        assert kwargs["cwd"] == edge_model_module.PROJECT_ROOT
        annotated_path.write_bytes(b"annotated")
        stdout = json.dumps(
            {
                "detections": [
                    {
                        "category": "insulator_surface_damage",
                        "deviceType": "insulator",
                        "faultType": "surface_damage",
                        "confidence": 0.77,
                        "bbox": [10, 20, 100, 200],
                    }
                ],
                "imageWidth": 640,
                "imageHeight": 480,
                "latencyMs": 26.5,
                "fps": 37.7,
                "annotatedImagePath": str(annotated_path),
            }
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(edge_model_module.subprocess, "run", fake_run)

    result = EdgeModelInferenceService().infer_frame(image_path, annotated_path)

    assert result is not None
    assert result.image_width == 640
    assert result.image_height == 480
    assert result.latency_ms == 26.5
    assert len(result.detections) == 1
    assert result.detections[0].faultType == "surface_damage"
    assert result.detections[0].bbox == (10, 20, 100, 200)
    assert result.annotated_image_path == annotated_path


def test_edge_model_service_degrades_when_model_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "edge_model_enabled", True)
    monkeypatch.setattr(settings, "edge_model_path", str(tmp_path / "missing.om"))
    monkeypatch.setattr(settings, "edge_model_script", str(tmp_path / "missing.py"))
    monkeypatch.setattr(settings, "edge_model_classes_path", str(tmp_path / "missing-classes.json"))
    monkeypatch.setattr(settings, "edge_model_preprocess_path", str(tmp_path / "missing-preprocess.json"))

    result = EdgeModelInferenceService().infer_frame(tmp_path / "frame.jpg", None)

    assert result is None
