from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="EDGEEYE_")

    app_name: str = "EdgeEye API"
    app_version: str = "0.1.0"
    database_path: str = "data/edgeeye.db"
    uploads_dir: str = "uploads"
    reports_dir: str = "reports"
    camera_bridge_enabled: bool = True
    camera_source: str = Field(default="/dev/video0", min_length=1)
    camera_capture_backend: Literal["ffmpeg", "v4l2", "auto"] = "ffmpeg"
    camera_ffmpeg_path: str = Field(default="ffmpeg", min_length=1)
    camera_v4l2_ctl_path: str = Field(default="v4l2-ctl", min_length=1)
    camera_width: int = Field(default=640, ge=1)
    camera_height: int = Field(default=480, ge=1)
    camera_interval_seconds: float = Field(default=5.0, gt=0)
    camera_stream_fps: int = Field(default=30, ge=1, le=60)
    camera_timeout_seconds: float = Field(default=5.0, gt=0)
    camera_max_raw_frames_per_inspection: int = Field(default=120, ge=1)
    camera_device_id: str = Field(default="device-001", min_length=1)
    camera_operator: str = Field(default="backend-camera", min_length=1)
    camera_outbox_dir: str = Field(default="data/camera-outbox", min_length=1)
    edge_model_enabled: bool = True
    edge_model_python: str = Field(default="python3", min_length=1)
    edge_model_script: str = Field(default="model-deploy/edge_acl_om_bridge.py", min_length=1)
    edge_model_path: str = Field(
        default="models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om",
        min_length=1,
    )
    edge_model_classes_path: str = Field(default="model-deploy/classes-edgeeye-insulator-v1.json", min_length=1)
    edge_model_preprocess_path: str = Field(default="model-deploy/preprocess-edgeeye-insulator-v1.json", min_length=1)
    edge_model_output_shape: str = Field(default="1,6,8400", min_length=1)
    edge_model_device_id: int = Field(default=0, ge=0)
    edge_model_timeout_seconds: float = Field(default=15.0, gt=0)
    edge_model_annotated_enabled: bool = True
    llm_provider: str = "rule-template"
    llm_api_url: str | None = None
    llm_api_key: str | None = None
    llm_model_name: str = "rule-template"
    llm_timeout_seconds: float = 10.0
    llm_max_retries: int = 2
    alarm_dedup_window_seconds: int = 300
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


settings = Settings()
