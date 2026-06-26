from __future__ import annotations

import hashlib
import html as html_lib
import io
import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable

from app.core.config import settings
from app.core.errors import ApiException
from app.models.dashboard import Dashboard, HighRiskAlarm
from app.models.inspection import (
    Advice,
    AdviceGenerateRequest,
    Alarm,
    Detection,
    DetectionUploadRequest,
    DetectionUploadResult,
    Device,
    EventItem,
    FailInspectionRequest,
    FinishInspectionRequest,
    InspectionListItem,
    InspectionStatusResult,
    LatestInspectionResult,
    PageResult,
    ReportDetail,
    ReportExport,
    ReportListItem,
    StartInspectionRequest,
    UpdateProcessStatusRequest,
)
from app.models.system import AtlasStatus, ModelStatus, SubsystemStatus, SystemOverview
from app.services.storage import SQLiteStore

BEIJING_TZ = timezone(timedelta(hours=8))
RULE_VERSION = "builtin-2026-06-17"
RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"
PDF_PAGE_WIDTH = 612
PDF_PAGE_HEIGHT = 792
PDF_LEFT_MARGIN = 72
PDF_RIGHT_MARGIN = 72
PDF_PRINTABLE_WIDTH = PDF_PAGE_WIDTH - PDF_LEFT_MARGIN - PDF_RIGHT_MARGIN
PDF_WRAP_BUDGET_PT = PDF_PRINTABLE_WIDTH - 8
PDF_LINE_HEIGHT = 16
PDF_TOP_MARGIN = 760
PDF_FOOTER_Y = 36
PDF_FONT_FULL = 10
PDF_FONT_TITLE = 18
PDF_FONT_HEADING = 13
PDF_FONT_FOOTER = 8
PDF_COLOR_TITLE = (0.13, 0.20, 0.45)
PDF_COLOR_HEADING = (0.20, 0.40, 0.80)
PDF_COLOR_BODY = (0.12, 0.14, 0.20)
PDF_COLOR_MUTED = (0.45, 0.50, 0.58)
PDF_COLOR_RULE = (0.66, 0.70, 0.76)
PDF_COLOR_DANGER = (0.80, 0.20, 0.20)
PDF_CJK_FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
PDF_CJK_FONT_NAME = "WQYZenHei"
FAULT_LABELS = {
    "surface_damage": "表面破损",
    "rust": "锈蚀",
    "foreign_object": "异物附着",
    "smoke": "烟雾",
    "fire": "明火",
    "person_intrusion": "人员闯入",
    "helmet_missing": "未佩戴安全帽",
    "unknown": "未知故障",
}
RISK_LABELS = {
    "none": "无风险",
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "严重风险",
}
DEVICE_NAME_LABELS = {
    "device-001": "2号线路绝缘子",
    "device-002": "变压器间隔",
    "device-003": "开关柜",
    "device-004": "断路器",
}
DEVICE_LOCATION_LABELS = {
    "Line 2 Area A": "2号线路 A 区",
    "Substation bay 1": "变电站 1 号间隔",
    "Distribution room": "配电室",
    "Feeder cabinet": "馈线柜",
    "unknown": "未知位置",
}
PROCESS_STATUS_LABELS = {
    "pending": "待处理",
    "processing": "处理中",
    "resolved": "已处理",
    "ignored": "已忽略",
}
ADVICE_STATUS_LABELS = {
    "none": "未生成",
    "generating": "生成中",
    "ready": "已生成",
    "fallback": "规则模板",
    "failed": "生成失败",
}


@dataclass
class _PdfItem:
    """A single renderable element in the PDF layout stream."""

    kind: str  # "text" | "rule" | "spacer"
    text: str = ""
    size: int = PDF_FONT_FULL
    color: tuple[float, float, float] = PDF_COLOR_BODY
    indent: int = 0
    height: int = PDF_LINE_HEIGHT


def current_timestamp() -> datetime:
    return datetime.now(BEIJING_TZ)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    return value.isoformat()


def _dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_load(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


def _payload_hash(payload: DetectionUploadRequest) -> str:
    body = payload.model_dump(mode="json")
    return hashlib.sha256(_json_dump(body).encode("utf-8")).hexdigest()


def _resolve_llm_provider_config() -> tuple[str | None, str | None, str]:
    provider = settings.llm_provider.strip().lower()
    api_url = settings.llm_api_url.strip() if settings.llm_api_url else None
    configured_model = settings.llm_model_name.strip()

    if provider == "deepseek":
        model_name = configured_model if configured_model and configured_model != "rule-template" else DEEPSEEK_DEFAULT_MODEL
        return api_url or DEEPSEEK_CHAT_COMPLETIONS_URL, model_name, provider

    return api_url, configured_model, provider


def _bounded_page(page: int, page_size: int) -> tuple[int, int, int]:
    safe_page = max(page, 1)
    safe_size = min(max(page_size, 1), 100)
    return safe_page, safe_size, (safe_page - 1) * safe_size


class InspectionService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def reset(self) -> None:
        self.store.reset()

    def start_inspection(self, request: StartInspectionRequest) -> InspectionStatusResult:
        now = current_timestamp()
        with self.store.connect() as connection:
            self._ensure_device(connection, request.deviceId, now)
            inspection_id = self._next_dated_id(connection, "inspections", "inspection_id", "inspection")
            connection.execute(
                """
                INSERT INTO inspections (
                    inspection_id, device_id, operator, source, status, started_at
                )
                VALUES (?, ?, ?, ?, 'running', ?)
                """,
                (inspection_id, request.deviceId, request.operator, request.source, _iso(now)),
            )
        return InspectionStatusResult(inspectionId=inspection_id, status="running")

    def finish_inspection(self, inspection_id: str, request: FinishInspectionRequest) -> InspectionStatusResult:
        ended_at = request.endedAt or current_timestamp()
        with self.store.connect() as connection:
            inspection = self._get_inspection_row(connection, inspection_id)
            if inspection is None:
                raise ApiException("NOT_FOUND", "inspection not found", status_code=404)
            if inspection["status"] not in {"pending", "running"}:
                raise ApiException(
                    "INVALID_STATE_TRANSITION",
                    "inspection cannot be finished from current state",
                    status_code=409,
                )
            connection.execute(
                """
                UPDATE inspections
                SET status = 'completed', ended_at = ?, summary = ?
                WHERE inspection_id = ?
                """,
                (_iso(ended_at), request.summary, inspection_id),
            )
            self._generate_report(connection, inspection_id, ended_at)
        return InspectionStatusResult(inspectionId=inspection_id, status="completed", endedAt=ended_at)

    def fail_inspection(self, inspection_id: str, request: FailInspectionRequest) -> InspectionStatusResult:
        ended_at = request.endedAt or current_timestamp()
        with self.store.connect() as connection:
            inspection = self._get_inspection_row(connection, inspection_id)
            if inspection is None:
                raise ApiException("NOT_FOUND", "inspection not found", status_code=404)
            if inspection["status"] not in {"pending", "running"}:
                raise ApiException(
                    "INVALID_STATE_TRANSITION",
                    "inspection cannot be failed from current state",
                    status_code=409,
                )
            connection.execute(
                """
                UPDATE inspections
                SET status = 'failed', ended_at = ?, failure_reason = ?
                WHERE inspection_id = ?
                """,
                (_iso(ended_at), request.reason, inspection_id),
            )
        return InspectionStatusResult(inspectionId=inspection_id, status="failed", endedAt=ended_at)

    def list_inspections(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        device_id: str | None = None,
    ) -> PageResult[InspectionListItem]:
        page, page_size, offset = _bounded_page(page, page_size)
        where, params = self._where_clause(
            [
                ("i.status = ?", status),
                ("i.device_id = ?", device_id),
            ]
        )
        with self.store.connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM inspections i {where}",
                params,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT
                    i.*,
                    d.device_name,
                    (SELECT COUNT(*) FROM faults f WHERE f.inspection_id = i.inspection_id) AS fault_count,
                    (
                        SELECT COUNT(*)
                        FROM alarms a
                        JOIN faults f ON f.fault_id = a.fault_id
                        WHERE f.inspection_id = i.inspection_id
                    ) AS alarm_count
                FROM inspections i
                JOIN devices d ON d.device_id = i.device_id
                {where}
                ORDER BY i.started_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return PageResult(
            items=[self._inspection_item_from_row(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )

    def upload_detection_result(self, payload: DetectionUploadRequest) -> DetectionUploadResult:
        now = current_timestamp()
        received_at = payload.receivedAt or now
        payload_hash = _payload_hash(payload)
        with self.store.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM detection_results WHERE idempotency_key = ?",
                (payload.idempotencyKey,),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise ApiException(
                        "IDEMPOTENCY_CONFLICT",
                        "same idempotency key was used for different content",
                        status_code=409,
                    )
                return self._upload_result_from_row(existing, duplicate=True)

            inspection = self._ensure_inspection_for_upload(connection, payload, received_at)
            result_id = self._next_id(connection, "detection_results", "result_id", "result")
            detections = self._enrich_detections(result_id, payload)
            faults_created = 0
            faults_updated = 0
            alarms_created = 0
            alarms_suppressed = 0

            for detection in detections:
                if detection.faultType is None:
                    continue
                fault, created = self._upsert_fault(connection, payload, inspection, detection, received_at)
                if created:
                    faults_created += 1
                else:
                    faults_updated += 1
                alarm_result = self._upsert_alarm(connection, fault, received_at)
                if alarm_result == "created":
                    alarms_created += 1
                elif alarm_result == "suppressed":
                    alarms_suppressed += 1

            report_triggered = faults_created > 0 or faults_updated > 0
            detection_payload = [item.model_dump(mode="json") for item in detections]
            try:
                connection.execute(
                    """
                    INSERT INTO detection_results (
                        result_id, idempotency_key, payload_hash, inspection_id, frame_id, frame_seq,
                        timestamp, received_at, processed_at, device_id, is_key_frame, upload_reason,
                        event_key, sample_window_json, image_url, annotated_image_url, image_width,
                        image_height, detections_json, performance_json, faults_created, faults_updated,
                        alarms_created, alarms_suppressed, report_triggered, warnings_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]')
                    """,
                    (
                        result_id,
                        payload.idempotencyKey,
                        payload_hash,
                        payload.inspectionId,
                        payload.frameId,
                        payload.frameSeq,
                        _iso(payload.timestamp),
                        _iso(received_at),
                        _iso(now),
                        payload.deviceId or inspection["device_id"],
                        int(payload.isKeyFrame),
                        payload.uploadReason,
                        payload.eventKey,
                        _json_dump(payload.sampleWindow.model_dump(mode="json")) if payload.sampleWindow else None,
                        payload.imageUrl,
                        payload.annotatedImageUrl,
                        payload.imageWidth,
                        payload.imageHeight,
                        _json_dump(detection_payload),
                        _json_dump(payload.performance.model_dump(mode="json")),
                        faults_created,
                        faults_updated,
                        alarms_created,
                        alarms_suppressed,
                        int(report_triggered),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ApiException(
                    "DUPLICATE_UPLOAD",
                    "inspection frame already has a saved detection result",
                    status_code=409,
                    details={"inspectionId": payload.inspectionId, "frameId": payload.frameId},
                ) from exc

            if report_triggered:
                self._generate_report(connection, payload.inspectionId, received_at, create_new=faults_created > 0)

            row = connection.execute(
                "SELECT * FROM detection_results WHERE result_id = ?",
                (result_id,),
            ).fetchone()
        return self._upload_result_from_row(row, duplicate=False)

    def get_latest_result(self, inspection_id: str) -> LatestInspectionResult:
        with self.store.connect() as connection:
            inspection = self._get_inspection_row(connection, inspection_id)
            if inspection is None:
                raise ApiException("NOT_FOUND", "inspection not found", status_code=404)
            row = connection.execute(
                """
                SELECT *
                FROM detection_results
                WHERE inspection_id = ?
                ORDER BY received_at DESC
                LIMIT 1
                """,
                (inspection_id,),
            ).fetchone()
            if row is None:
                raise ApiException("RESULT_NOT_READY", "inspection has no frame result yet", status_code=404)
            faults = [
                self._fault_from_row(item)
                for item in connection.execute(
                    """
                    SELECT *
                    FROM faults
                    WHERE inspection_id = ?
                    ORDER BY last_seen_at DESC
                    """,
                    (inspection_id,),
                ).fetchall()
            ]
        received_at = _dt(row["received_at"])
        result_status = "ready"
        if received_at is not None and current_timestamp() - received_at > timedelta(milliseconds=3000):
            result_status = "stale"
        return LatestInspectionResult(
            idempotencyKey=row["idempotency_key"],
            inspectionId=row["inspection_id"],
            frameId=row["frame_id"],
            frameSeq=row["frame_seq"],
            timestamp=_dt(row["timestamp"]),
            receivedAt=received_at,
            deviceId=row["device_id"],
            isKeyFrame=bool(row["is_key_frame"]),
            uploadReason=row["upload_reason"],
            eventKey=row["event_key"],
            sampleWindow=_json_load(row["sample_window_json"]),
            imageUrl=row["image_url"],
            annotatedImageUrl=row["annotated_image_url"],
            imageWidth=row["image_width"],
            imageHeight=row["image_height"],
            detections=[Detection(**item) for item in _json_load(row["detections_json"], [])],
            performance=_json_load(row["performance_json"], {}),
            inspectionStatus=inspection["status"],
            resultStatus=result_status,
            staleAfterMs=3000,
            eventStatus=faults[0].eventStatus if faults else None,
            faults=faults,
        )

    def list_devices(
        self,
        *,
        device_type: str | None = None,
        status: str | None = None,
    ) -> PageResult[Device]:
        where, params = self._where_clause(
            [
                ("device_type = ?", device_type),
                ("status = ?", status),
            ]
        )
        with self.store.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM devices {where} ORDER BY device_id",
                params,
            ).fetchall()
        return PageResult(
            items=[self._device_from_row(row) for row in rows],
            total=len(rows),
            page=1,
            pageSize=max(len(rows), 1),
        )

    def list_faults(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        risk_level: str | None = None,
        process_status: str | None = None,
        device_id: str | None = None,
    ) -> PageResult[Any]:
        page, page_size, offset = _bounded_page(page, page_size)
        where, params = self._where_clause(
            [
                ("risk_level = ?", risk_level),
                ("process_status = ?", process_status),
                ("device_id = ?", device_id),
            ]
        )
        with self.store.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM faults {where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM faults {where} ORDER BY last_seen_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()
        return PageResult(
            items=[self._fault_from_row(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )

    def list_alarms(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        alarm_level: str | None = None,
        process_status: str | None = None,
    ) -> PageResult[Any]:
        page, page_size, offset = _bounded_page(page, page_size)
        where, params = self._where_clause(
            [
                ("alarm_level = ?", alarm_level),
                ("process_status = ?", process_status),
            ]
        )
        with self.store.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM alarms {where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM alarms {where} ORDER BY last_triggered_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()
        return PageResult(
            items=[self._alarm_from_row(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )

    def list_events(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        risk_level: str | None = None,
        process_status: str | None = None,
        advice_status: str | None = None,
    ) -> PageResult[EventItem]:
        page, page_size, offset = _bounded_page(page, page_size)
        where_parts = []
        params: list[Any] = []
        for condition, value in [
            ("f.risk_level = ?", risk_level),
            ("f.process_status = ?", process_status),
            ("COALESCE(ad.advice_status, 'none') = ?", advice_status),
        ]:
            if value is not None:
                where_parts.append(condition)
                params.append(value)
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        with self.store.connect() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM faults f
                LEFT JOIN advice ad ON ad.fault_id = f.fault_id
                {where}
                """,
                params,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT
                    f.*,
                    d.device_name,
                    a.alarm_id,
                    COALESCE(ad.advice_status, 'none') AS advice_status
                FROM faults f
                JOIN devices d ON d.device_id = f.device_id
                LEFT JOIN alarms a ON a.fault_id = f.fault_id
                LEFT JOIN advice ad ON ad.fault_id = f.fault_id
                {where}
                ORDER BY f.last_seen_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return PageResult(
            items=[self._event_from_row(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )

    def update_fault_status(self, fault_id: str, request: UpdateProcessStatusRequest) -> Any:
        handled_at = current_timestamp()
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM faults WHERE fault_id = ?", (fault_id,)).fetchone()
            if row is None:
                raise ApiException("NOT_FOUND", "fault not found", status_code=404)
            connection.execute(
                """
                UPDATE faults
                SET process_status = ?, last_handled_by = ?, last_handled_at = ?, last_handle_note = ?
                WHERE fault_id = ?
                """,
                (request.processStatus, request.operator, _iso(handled_at), request.note, fault_id),
            )
            updated = connection.execute("SELECT * FROM faults WHERE fault_id = ?", (fault_id,)).fetchone()
        return self._fault_from_row(updated)

    def update_alarm_status(self, alarm_id: str, request: UpdateProcessStatusRequest) -> Alarm:
        handled_at = current_timestamp()
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM alarms WHERE alarm_id = ?", (alarm_id,)).fetchone()
            if row is None:
                raise ApiException("NOT_FOUND", "alarm not found", status_code=404)
            connection.execute(
                """
                UPDATE alarms
                SET process_status = ?, last_handled_by = ?, last_handled_at = ?, last_handle_note = ?
                WHERE alarm_id = ?
                """,
                (request.processStatus, request.operator, _iso(handled_at), request.note, alarm_id),
            )
            updated = connection.execute("SELECT * FROM alarms WHERE alarm_id = ?", (alarm_id,)).fetchone()
        return self._alarm_from_row(updated)

    def generate_advice(self, request: AdviceGenerateRequest) -> Advice:
        now = current_timestamp()
        with self.store.connect() as connection:
            fault = connection.execute("SELECT * FROM faults WHERE fault_id = ?", (request.faultId,)).fetchone()
            if fault is None:
                raise ApiException("NOT_FOUND", "fault not found", status_code=404)
            existing = connection.execute("SELECT * FROM advice WHERE fault_id = ?", (request.faultId,)).fetchone()
            if existing is not None:
                return self._advice_from_row(existing)

            advice_id = self._next_id(connection, "advice", "advice_id", "advice")
            generated, model_name, advice_status = self._generate_advice_payload(fault)
            connection.execute(
                """
                INSERT INTO advice (
                    advice_id, fault_id, possible_causes_json, risk_analysis,
                    inspection_steps_json, maintenance_suggestions_json, safety_notes_json,
                    model_name, advice_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    advice_id,
                    request.faultId,
                    _json_dump(generated["possibleCauses"]),
                    generated["riskAnalysis"],
                    _json_dump(generated["inspectionSteps"]),
                    _json_dump(generated["maintenanceSuggestions"]),
                    _json_dump(generated["safetyNotes"]),
                    model_name,
                    advice_status,
                    _iso(now),
                ),
            )
            row = connection.execute("SELECT * FROM advice WHERE advice_id = ?", (advice_id,)).fetchone()
        return self._advice_from_row(row)

    def get_fault_advice(self, fault_id: str) -> Advice:
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM advice WHERE fault_id = ?", (fault_id,)).fetchone()
            if row is None:
                fault = connection.execute("SELECT 1 FROM faults WHERE fault_id = ?", (fault_id,)).fetchone()
                if fault is None:
                    raise ApiException("NOT_FOUND", "fault not found", status_code=404)
                raise ApiException("ADVICE_NOT_READY", "advice has not been generated", status_code=404)
        return self._advice_from_row(row)

    def list_reports(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        inspection_id: str | None = None,
    ) -> PageResult[ReportListItem]:
        page, page_size, offset = _bounded_page(page, page_size)
        where, params = self._where_clause([("inspection_id = ?", inspection_id)])
        with self.store.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM reports {where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM reports {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()
        return PageResult(
            items=[self._report_list_item_from_row(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )

    def get_report(self, report_id: str) -> ReportDetail:
        with self.store.connect() as connection:
            report = connection.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
            if report is None:
                raise ApiException("NOT_FOUND", "report not found", status_code=404)
            inspection = self._get_inspection_row(connection, report["inspection_id"])
            device = connection.execute(
                "SELECT * FROM devices WHERE device_id = ?",
                (inspection["device_id"],),
            ).fetchone()
            faults = [
                self._fault_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM faults WHERE inspection_id = ? ORDER BY last_seen_at DESC",
                    (report["inspection_id"],),
                ).fetchall()
            ]
            alarms = [
                self._alarm_from_row(row)
                for row in connection.execute(
                    """
                    SELECT a.*
                    FROM alarms a
                    JOIN faults f ON f.fault_id = a.fault_id
                    WHERE f.inspection_id = ?
                    ORDER BY a.last_triggered_at DESC
                    """,
                    (report["inspection_id"],),
                ).fetchall()
            ]
            advices = [
                self._advice_from_row(row)
                for row in connection.execute(
                    """
                    SELECT ad.*
                    FROM advice ad
                    JOIN faults f ON f.fault_id = ad.fault_id
                    WHERE f.inspection_id = ?
                    ORDER BY ad.created_at DESC
                    """,
                    (report["inspection_id"],),
                ).fetchall()
            ]
        base = self._report_list_item_from_row(report)
        return ReportDetail(
            **base.model_dump(),
            summary=report["summary"],
            device=self._device_from_row(device),
            faults=faults,
            alarms=alarms,
            advices=advices,
            exports=[ReportExport(**item) for item in _json_load(report["exports_json"], [])],
        )

    def export_report(self, report_id: str, report_format: str = "html") -> ReportExport:
        with self.store.connect() as connection:
            report = connection.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
            if report is None:
                raise ApiException("NOT_FOUND", "report not found", status_code=404)
            document = self._build_report_document(connection, report["inspection_id"], report_id=report_id)
            generated_at = current_timestamp()
            file_name = f"{report_id}.{report_format}"
            download_url = f"/reports/{file_name}"
            if report_format == "pdf":
                self._write_pdf_report(document, file_name)
            else:
                self._write_html_report(document, file_name)
            export = ReportExport(
                format=report_format,
                exportStatus="ready",
                downloadUrl=download_url,
                fileName=file_name,
                generatedAt=generated_at,
                expiresAt=None,
            )
            exports = [
                item
                for item in _json_load(report["exports_json"], [])
                if item.get("format") != report_format
            ]
            exports.append(export.model_dump(mode="json"))
            connection.execute(
                "UPDATE reports SET exports_json = ? WHERE report_id = ?",
                (_json_dump(exports), report_id),
            )
        return export

    def get_dashboard(self) -> Dashboard:
        with self.store.connect() as connection:
            device_count = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            inspection_count = connection.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
            fault_count = connection.execute("SELECT COUNT(*) FROM faults").fetchone()[0]
            alarm_count = connection.execute("SELECT COUNT(*) FROM alarms").fetchone()[0]
            critical_alarm_count = connection.execute(
                "SELECT COUNT(*) FROM alarms WHERE alarm_level = 'critical'"
            ).fetchone()[0]
            active_inspection_count = connection.execute(
                "SELECT COUNT(*) FROM inspections WHERE status = 'running'"
            ).fetchone()[0]
            unresolved_fault_count = connection.execute(
                "SELECT COUNT(*) FROM faults WHERE process_status IN ('pending', 'processing')"
            ).fetchone()[0]
            unresolved_alarm_count = connection.execute(
                "SELECT COUNT(*) FROM alarms WHERE process_status IN ('pending', 'processing')"
            ).fetchone()[0]
            latest_inspection_at = connection.execute("SELECT MAX(started_at) FROM inspections").fetchone()[0]
            latest_alarm = connection.execute(
                """
                SELECT
                    a.alarm_id,
                    a.fault_id,
                    f.inspection_id,
                    f.device_id,
                    d.device_name,
                    f.fault_type,
                    f.risk_level,
                    a.alarm_level,
                    a.process_status,
                    a.created_at
                FROM alarms a
                JOIN faults f ON f.fault_id = a.fault_id
                JOIN devices d ON d.device_id = f.device_id
                WHERE f.risk_level IN ('high', 'critical')
                ORDER BY a.created_at DESC
                LIMIT 1
                """
            ).fetchone()
        return Dashboard(
            deviceCount=device_count,
            inspectionCount=inspection_count,
            faultCount=fault_count,
            alarmCount=alarm_count,
            criticalAlarmCount=critical_alarm_count,
            activeInspectionCount=active_inspection_count,
            unresolvedFaultCount=unresolved_fault_count,
            unresolvedAlarmCount=unresolved_alarm_count,
            dataFreshness="fresh",
            pageState="ready" if device_count else "empty",
            latestInspectionAt=_dt(latest_inspection_at),
            latestHighRiskAlarm=self._high_risk_alarm_from_row(latest_alarm) if latest_alarm else None,
        )

    def get_system_overview(self) -> SystemOverview:
        now = current_timestamp()
        with self.store.connect() as connection:
            active_inspection_count = connection.execute(
                "SELECT COUNT(*) FROM inspections WHERE status = 'running'"
            ).fetchone()[0]
            unresolved_fault_count = connection.execute(
                "SELECT COUNT(*) FROM faults WHERE process_status IN ('pending', 'processing')"
            ).fetchone()[0]
            unresolved_alarm_count = connection.execute(
                "SELECT COUNT(*) FROM alarms WHERE process_status IN ('pending', 'processing')"
            ).fetchone()[0]
            latest = connection.execute(
                "SELECT * FROM detection_results ORDER BY received_at DESC LIMIT 1"
            ).fetchone()
        performance = _json_load(latest["performance_json"], {}) if latest else {}
        last_frame_at = _dt(latest["timestamp"]) if latest else None
        heartbeat_at = _dt(latest["received_at"]) if latest else now
        return SystemOverview(
            camera=SubsystemStatus(
                status="online" if latest else "unknown",
                lastFrameAt=last_frame_at,
                lastHeartbeatAt=heartbeat_at,
                message="camera stream is healthy" if latest else "waiting for first frame",
                degradedReason=None,
            ),
            atlas=AtlasStatus(
                status="online" if latest else "unknown",
                lastHeartbeatAt=heartbeat_at,
                message="edge app is uploading key frames" if latest else "waiting for Atlas upload",
                degradedReason=None,
                cpuUsage=performance.get("cpuUsage", 0),
                memoryUsage=performance.get("memoryUsage", 0),
                npuUsage=performance.get("npuUsage", 0),
            ),
            model=ModelStatus(
                status="online" if latest else "unknown",
                lastHeartbeatAt=heartbeat_at,
                message="model inference is healthy" if latest else "waiting for inference result",
                degradedReason=None,
                modelVersion="detector-v1",
                fps=performance.get("fps", 0),
                latencyMs=int(performance.get("latencyMs", 0)),
            ),
            backend=SubsystemStatus(
                status="online",
                lastHeartbeatAt=now,
                message="api and database are healthy",
                degradedReason=None,
            ),
            updatedAt=now,
            dataFreshness="fresh",
            activeInspectionCount=active_inspection_count,
            unresolvedFaultCount=unresolved_fault_count,
            unresolvedAlarmCount=unresolved_alarm_count,
        )

    def _ensure_inspection_for_upload(
        self,
        connection: sqlite3.Connection,
        payload: DetectionUploadRequest,
        received_at: datetime,
    ) -> sqlite3.Row:
        inspection = self._get_inspection_row(connection, payload.inspectionId)
        if inspection is not None:
            if inspection["status"] not in {"pending", "running"}:
                raise ApiException(
                    "INSPECTION_NOT_RUNNING",
                    "inspection is not accepting detection uploads",
                    status_code=409,
                )
            if inspection["status"] == "pending":
                connection.execute(
                    "UPDATE inspections SET status = 'running' WHERE inspection_id = ?",
                    (payload.inspectionId,),
                )
            return self._get_inspection_row(connection, payload.inspectionId)

        device_id = payload.deviceId or "device-unknown"
        self._ensure_device(connection, device_id, received_at)
        connection.execute(
            """
            INSERT INTO inspections (
                inspection_id, device_id, operator, source, status, started_at
            )
            VALUES (?, ?, 'atlas', 'atlas', 'running', ?)
            """,
            (payload.inspectionId, device_id, _iso(received_at)),
        )
        return self._get_inspection_row(connection, payload.inspectionId)

    def _upsert_fault(
        self,
        connection: sqlite3.Connection,
        payload: DetectionUploadRequest,
        inspection: sqlite3.Row,
        detection: Detection,
        seen_at: datetime,
    ) -> tuple[Any, bool]:
        device_id = payload.deviceId or inspection["device_id"]
        device = self._ensure_device(connection, device_id, seen_at)
        fault_type = detection.faultType or "unknown"
        device_type = detection.deviceType or device["device_type"] or "unknown"
        risk_level, alarm_level, priority = self._classify_fault(fault_type, detection.confidence)
        base_event_key = payload.eventKey or f"{payload.inspectionId}:{device_id}:{fault_type}"
        event_status = "resolved" if payload.uploadReason == "fault_resolved" else "ongoing"
        existing = self._find_fault_for_detection(connection, base_event_key, event_status)
        if existing is None:
            fault_id = self._next_id(connection, "faults", "fault_id", "fault")
            event_key = self._next_fault_event_key(connection, base_event_key)
            connection.execute(
                """
                INSERT INTO faults (
                    fault_id, inspection_id, device_id, device_type, fault_type, confidence,
                    risk_level, alarm_required, alarm_level, priority, process_status, event_key,
                    event_status, first_seen_at, last_seen_at, occurrence_count, last_confidence,
                    max_confidence, best_frame_id, best_image_url, best_annotated_image_url,
                    location, created_at, rule_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fault_id,
                    payload.inspectionId,
                    device_id,
                    device_type,
                    fault_type,
                    detection.confidence,
                    risk_level,
                    int(risk_level != "none"),
                    alarm_level,
                    priority,
                    "resolved" if event_status == "resolved" else "pending",
                    event_key,
                    event_status,
                    _iso(seen_at),
                    _iso(seen_at),
                    detection.confidence,
                    detection.confidence,
                    payload.frameId,
                    payload.imageUrl,
                    payload.annotatedImageUrl,
                    device["location"],
                    _iso(seen_at),
                    RULE_VERSION,
                ),
            )
            row = connection.execute("SELECT * FROM faults WHERE fault_id = ?", (fault_id,)).fetchone()
            return self._fault_from_row(row), True

        max_confidence = max(existing["max_confidence"], detection.confidence)
        best_frame_id = existing["best_frame_id"]
        best_image_url = existing["best_image_url"]
        best_annotated_image_url = existing["best_annotated_image_url"]
        if (
            RISK_ORDER[risk_level] > RISK_ORDER[existing["risk_level"]]
            or detection.confidence >= existing["max_confidence"]
        ):
            best_frame_id = payload.frameId
            best_image_url = payload.imageUrl
            best_annotated_image_url = payload.annotatedImageUrl
        merged_risk = risk_level
        merged_alarm = alarm_level
        merged_priority = priority
        if RISK_ORDER[existing["risk_level"]] > RISK_ORDER[risk_level]:
            merged_risk = existing["risk_level"]
            merged_alarm = existing["alarm_level"]
            merged_priority = existing["priority"]
        connection.execute(
            """
            UPDATE faults
            SET
                confidence = ?,
                risk_level = ?,
                alarm_required = ?,
                alarm_level = ?,
                priority = ?,
                process_status = ?,
                event_status = ?,
                last_seen_at = ?,
                occurrence_count = occurrence_count + 1,
                last_confidence = ?,
                max_confidence = ?,
                best_frame_id = ?,
                best_image_url = ?,
                best_annotated_image_url = ?
            WHERE fault_id = ?
            """,
            (
                detection.confidence,
                merged_risk,
                int(merged_risk != "none"),
                merged_alarm,
                merged_priority,
                self._next_fault_process_status(existing["process_status"], event_status),
                event_status,
                _iso(seen_at),
                detection.confidence,
                max_confidence,
                best_frame_id,
                best_image_url,
                best_annotated_image_url,
                existing["fault_id"],
            ),
        )
        row = connection.execute("SELECT * FROM faults WHERE fault_id = ?", (existing["fault_id"],)).fetchone()
        return self._fault_from_row(row), False

    def _next_fault_process_status(self, existing_process_status: str, event_status: str) -> str:
        if event_status == "resolved":
            return "resolved"
        return existing_process_status

    def _find_fault_for_detection(
        self,
        connection: sqlite3.Connection,
        base_event_key: str,
        event_status: str,
    ) -> sqlite3.Row | None:
        active = connection.execute(
            """
            SELECT *
            FROM faults
            WHERE (event_key = ? OR event_key LIKE ? ESCAPE '!')
              AND process_status IN ('pending', 'processing')
            ORDER BY last_seen_at DESC
            LIMIT 1
            """,
            self._event_key_scope_params(base_event_key),
        ).fetchone()
        if active is not None:
            return active

        latest = connection.execute(
            """
            SELECT *
            FROM faults
            WHERE event_key = ? OR event_key LIKE ? ESCAPE '!'
            ORDER BY last_seen_at DESC
            LIMIT 1
            """,
            self._event_key_scope_params(base_event_key),
        ).fetchone()
        if latest is None:
            return None
        if event_status == "resolved":
            return latest
        if latest["process_status"] in {"resolved", "ignored"}:
            return None
        return latest

    def _next_fault_event_key(self, connection: sqlite3.Connection, base_event_key: str) -> str:
        rows = connection.execute(
            """
            SELECT event_key
            FROM faults
            WHERE event_key = ? OR event_key LIKE ? ESCAPE '!'
            """,
            self._event_key_scope_params(base_event_key),
        ).fetchall()
        existing = {row["event_key"] for row in rows}
        if not existing:
            return base_event_key

        index = len(existing) + 1
        while True:
            candidate = f"{base_event_key}:occurrence-{index:04d}"
            if candidate not in existing:
                return candidate
            index += 1

    def _event_key_scope_params(self, base_event_key: str) -> tuple[str, str]:
        return base_event_key, f"{self._escape_like(base_event_key)}:%"

    def _escape_like(self, value: str) -> str:
        return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")

    def _upsert_alarm(self, connection: sqlite3.Connection, fault: Any, triggered_at: datetime) -> str | None:
        if not fault.alarmRequired:
            return None
        dedup_key = f"{fault.deviceId}:{fault.faultType}:{fault.alarmLevel}"
        existing = connection.execute("SELECT * FROM alarms WHERE dedup_key = ?", (dedup_key,)).fetchone()
        if existing is not None:
            process_status = existing["process_status"]
            reopen_delta = 0
            # A closed alarm only reopens when the new occurrence falls outside the
            # dedup window; within the window it stays suppressed (see contracts.md).
            if process_status in {"resolved", "ignored"} and self._dedup_window_elapsed(
                existing["last_triggered_at"], triggered_at
            ):
                process_status = "pending"
                reopen_delta = 1
            connection.execute(
                """
                UPDATE alarms
                SET last_triggered_at = ?,
                    suppressed_count = suppressed_count + 1,
                    process_status = ?,
                    reopen_count = reopen_count + ?
                WHERE alarm_id = ?
                """,
                (_iso(triggered_at), process_status, reopen_delta, existing["alarm_id"]),
            )
            return "suppressed"

        alarm_id = self._next_id(connection, "alarms", "alarm_id", "alarm")
        connection.execute(
            """
            INSERT INTO alarms (
                alarm_id, fault_id, device_id, alarm_level, risk_level, message, process_status,
                dedup_key, first_triggered_at, last_triggered_at, suppressed_count, reopen_count,
                created_at, rule_version
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                alarm_id,
                fault.faultId,
                fault.deviceId,
                fault.alarmLevel,
                fault.riskLevel,
                self._alarm_message(fault.faultType, fault.riskLevel),
                dedup_key,
                _iso(triggered_at),
                _iso(triggered_at),
                _iso(triggered_at),
                RULE_VERSION,
            ),
        )
        return "created"

    def _dedup_window_elapsed(self, last_triggered_at: str | None, triggered_at: datetime) -> bool:
        window_seconds = settings.alarm_dedup_window_seconds
        if window_seconds <= 0:
            return True
        last = _dt(last_triggered_at)
        if last is None:
            return True
        if last.tzinfo is None and triggered_at.tzinfo is not None:
            last = last.replace(tzinfo=triggered_at.tzinfo)
        elif last.tzinfo is not None and triggered_at.tzinfo is None:
            triggered_at = triggered_at.replace(tzinfo=last.tzinfo)
        return triggered_at - last > timedelta(seconds=window_seconds)

    def _generate_report(
        self,
        connection: sqlite3.Connection,
        inspection_id: str,
        generated_at: datetime,
        *,
        create_new: bool = False,
    ) -> None:
        existing = None
        if not create_new:
            existing = connection.execute(
                """
                SELECT *
                FROM reports
                WHERE inspection_id = ? AND format = 'html'
                ORDER BY version DESC
                LIMIT 1
                """,
                (inspection_id,),
            ).fetchone()
        report_id = existing["report_id"] if existing else self._next_report_id(connection, generated_at)
        version = existing["version"] if existing else self._next_report_version(connection, inspection_id)
        document = self._build_report_document(connection, inspection_id, report_id=report_id)
        title = document["title"]
        summary = document["summary"]
        url = f"/reports/{report_id}.html"
        exports = [
            {
                "format": "html",
                "exportStatus": "ready",
                "downloadUrl": url,
                "fileName": f"{report_id}.html",
                "generatedAt": _iso(generated_at),
                "expiresAt": None,
            }
        ]
        if existing:
            connection.execute(
                """
                UPDATE reports
                SET title = ?, summary = ?, report_status = 'ready', url = ?, created_at = ?, exports_json = ?
                WHERE report_id = ?
                """,
                (title, summary, url, _iso(generated_at), _json_dump(exports), report_id),
            )
            self._write_html_report(document, f"{report_id}.html")
            return
        connection.execute(
            """
            INSERT INTO reports (
                report_id, inspection_id, title, summary, report_status, format, url, created_at, exports_json, version
            )
            VALUES (?, ?, ?, ?, 'ready', 'html', ?, ?, ?, ?)
            """,
            (report_id, inspection_id, title, summary, url, _iso(generated_at), _json_dump(exports), version),
        )
        self._write_html_report(document, f"{report_id}.html")

    def _build_report_document(
        self,
        connection: sqlite3.Connection,
        inspection_id: str,
        *,
        report_id: str,
    ) -> dict[str, Any]:
        inspection = self._get_inspection_row(connection, inspection_id)
        device = connection.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (inspection["device_id"],),
        ).fetchone()
        faults = connection.execute(
            "SELECT * FROM faults WHERE inspection_id = ? ORDER BY last_seen_at DESC",
            (inspection_id,),
        ).fetchall()
        alarms = connection.execute(
            """
            SELECT a.*
            FROM alarms a
            JOIN faults f ON f.fault_id = a.fault_id
            WHERE f.inspection_id = ?
            ORDER BY a.last_triggered_at DESC
            """,
            (inspection_id,),
        ).fetchall()
        advice_by_fault_id = {
            row["fault_id"]: row
            for row in connection.execute(
                """
                SELECT ad.*
                FROM advice ad
                JOIN faults f ON f.fault_id = ad.fault_id
                WHERE f.inspection_id = ?
                ORDER BY ad.created_at DESC
                """,
                (inspection_id,),
            ).fetchall()
        }
        primary_fault = self._primary_fault(faults)
        device_name = self._device_display_name(device)
        location = self._location_display_name(device["location"])
        title = (
            f"{device_name} {self._fault_display_name(primary_fault)}巡检报告"
            if primary_fault
            else f"{device_name} 巡检报告"
        )
        high_risk_count = sum(1 for fault in faults if fault["risk_level"] in {"high", "critical"})
        highest_risk = self._highest_risk_level(faults)
        conclusion = self._report_conclusion(
            fault_count=len(faults),
            alarm_count=len(alarms),
            high_risk_count=high_risk_count,
            highest_risk=highest_risk,
        )
        summary = (
            f"本次巡检发现 {len(faults)} 项故障、触发 {len(alarms)} 条告警，"
            f"其中高风险及以上 {high_risk_count} 项。"
        )
        fault_sections = []
        for fault in faults:
            advice = advice_by_fault_id.get(fault["fault_id"])
            alarm = next((item for item in alarms if item["fault_id"] == fault["fault_id"]), None)
            fault_sections.append(
                {
                    "faultId": fault["fault_id"],
                    "title": self._alarm_message(fault["fault_type"], fault["risk_level"]),
                    "faultTypeLabel": self._fault_display_name(fault),
                    "riskLabel": RISK_LABELS.get(fault["risk_level"], fault["risk_level"]),
                    "confidence": fault["confidence"],
                    "bestFrameId": fault["best_frame_id"],
                    "bestImageUrl": fault["best_annotated_image_url"] or fault["best_image_url"],
                    "processStatus": fault["process_status"],
                    "processStatusLabel": PROCESS_STATUS_LABELS.get(fault["process_status"], fault["process_status"]),
                    "occurrenceCount": fault["occurrence_count"],
                    "firstSeenAt": fault["first_seen_at"],
                    "lastSeenAt": fault["last_seen_at"],
                    "lastHandledBy": fault["last_handled_by"] or "未记录",
                    "lastHandledAt": fault["last_handled_at"],
                    "alarmMessage": alarm["message"] if alarm else "未触发告警",
                    "alarmStatusLabel": (
                        PROCESS_STATUS_LABELS.get(alarm["process_status"], alarm["process_status"])
                        if alarm
                        else "未触发"
                    ),
                    "advice": self._report_advice_section(advice) if advice else None,
                }
            )
        return {
            "report_id": report_id,
            "inspection_id": inspection_id,
            "title": title,
            "summary": summary,
            "conclusion": conclusion,
            "deviceName": device_name,
            "location": location,
            "startedAt": inspection["started_at"],
            "endedAt": inspection["ended_at"],
            "highestRiskLabel": RISK_LABELS.get(highest_risk, highest_risk),
            "faultCount": len(faults),
            "alarmCount": len(alarms),
            "highRiskCount": high_risk_count,
            "faults": fault_sections,
        }

    def _reports_dir(self) -> Path:
        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir

    def _write_html_report(self, report: dict[str, Any], file_name: str) -> None:
        title = report["title"]
        summary = report["summary"]
        fault_sections = "".join(self._html_fault_section(fault) for fault in report["faults"])
        conclusion = report["conclusion"]
        html_content = (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{html_lib.escape(title)}</title>"
            "<style>"
            "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.65;margin:32px;color:#172033;background:#f7f9fc;}"
            "main{max-width:920px;margin:0 auto;background:#fff;border:1px solid #d8dee8;border-radius:10px;padding:28px;}"
            "h1{font-size:26px;margin:0 0 8px;}h2{font-size:18px;margin:28px 0 10px;border-bottom:1px solid #d8dee8;padding-bottom:6px;}"
            "h3{font-size:15px;margin:18px 0 8px}.meta{color:#5b667a}.lead{font-size:16px;color:#2f3b52;}"
            ".summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0;}"
            ".summary-card{border:1px solid #d8dee8;border-radius:8px;padding:12px;background:#fbfcff;}.summary-card span{display:block;color:#5b667a;font-size:12px}.summary-card strong{font-size:18px;}"
            ".section{border:1px solid #d8dee8;border-radius:8px;padding:16px;margin-top:16px;background:#fff;}"
            ".finding{border-left:4px solid #2563eb;background:#eff6ff;padding:12px 14px;border-radius:6px;margin:16px 0;}"
            "ul{padding-left:22px}.evidence{color:#5b667a;font-size:13px;word-break:break-all;}"
            "</style></head><body>"
            "<main>"
            f"<h1>{html_lib.escape(title)}</h1><p class=\"lead\">{html_lib.escape(summary)}</p>"
            f"<p class=\"meta\">报告编号：{html_lib.escape(report['report_id'])} / 巡检编号：{html_lib.escape(report['inspection_id'])}</p>"
            "<section>"
            "<h2>一、巡检结论</h2>"
            f"<div class=\"finding\"><strong>{html_lib.escape(conclusion['priority'])}</strong><br>{html_lib.escape(conclusion['finding'])}<br>{html_lib.escape(conclusion['action'])}</div>"
            f"<p>{html_lib.escape(conclusion['alarmSummary'])}</p>"
            "<div class=\"summary-grid\">"
            f"<div class=\"summary-card\"><span>最高风险</span><strong>{html_lib.escape(report['highestRiskLabel'])}</strong></div>"
            f"<div class=\"summary-card\"><span>故障数量</span><strong>{report['faultCount']}</strong></div>"
            f"<div class=\"summary-card\"><span>告警数量</span><strong>{report['alarmCount']}</strong></div>"
            f"<div class=\"summary-card\"><span>高风险及以上</span><strong>{report['highRiskCount']}</strong></div>"
            "</div></section>"
            "<section>"
            "<h2>二、巡检对象</h2>"
            f"<p>设备：{html_lib.escape(report['deviceName'])}</p>"
            f"<p>位置：{html_lib.escape(report['location'])}</p>"
            f"<p>开始时间：{html_lib.escape(self._report_time(report['startedAt']))} / 结束时间：{html_lib.escape(self._report_time(report['endedAt']))}</p>"
            "</section>"
            "<section><h2>三、故障发现与处置建议</h2>"
            f"{fault_sections or '<p>本次巡检未发现故障。</p>'}"
            "</section>"
            "</main>"
            "</body></html>"
        )
        (self._reports_dir() / file_name).write_text(html_content, encoding="utf-8")

    def _write_pdf_report(self, report: dict[str, Any], file_name: str) -> None:
        items = self._build_pdf_items(report)
        report_id = str(report["report_id"])
        footer_chars = f"{report_id}  ·  第 {1} 页 / 共 {9} 页"
        all_text = "".join(item.text for item in items) + footer_chars
        font = self._build_embedded_font(all_text)
        if font is not None:
            char_width_pt = lambda ch: self._embedded_char_width_pt(ch, font)
            glyph_hex = lambda text: self._pdf_identity_hex(text, font["cid_map"])
        else:
            char_width_pt = self._pdf_char_width_pt
            glyph_hex = self._pdf_hex_text
        pages = self._layout_pdf_pages(items, char_width_pt=char_width_pt)
        total_pages = len(pages)
        streams = [
            self._pdf_page_stream(
                page,
                page_no=index + 1,
                total_pages=total_pages,
                report_id=report_id,
                glyph_hex=glyph_hex,
            )
            for index, page in enumerate(pages)
        ]
        kids = " ".join(f"{obj_id} 0 R" for obj_id in self._pdf_page_object_ids(len(streams), font)).encode("ascii")
        objects = self._pdf_font_and_page_objects(
            font=font,
            kids=kids,
            page_count=len(streams),
            content_object_ids=self._pdf_content_object_ids(len(streams), font),
            streams=streams,
        )
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref_at = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
        )
        (self._reports_dir() / file_name).write_bytes(bytes(pdf))

    def _pdf_font_and_page_objects(
        self,
        *,
        font: dict[str, Any] | None,
        kids: bytes,
        page_count: int,
        content_object_ids: list[int],
        streams: list[bytes],
    ) -> list[bytes]:
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(page_count).encode("ascii") + b" >>",
        ]
        if font is None:
            objects += [
                b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>",
                b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo 5 0 R /DW 1000 >>",
                b"<< /Registry (Adobe) /Ordering (GB1) /Supplement 2 >>",
            ]
        else:
            name = PDF_CJK_FONT_NAME.encode("ascii")
            desc = font["desc"]
            w_array = self._pdf_w_array_bytes(font["widths"])
            bbox = " ".join(str(v) for v in desc["bbox"]).encode("ascii")
            objects += [
                b"<< /Type /Font /Subtype /Type0 /BaseFont /" + name + b" /Encoding /Identity-H /DescendantFonts [4 0 R] >>",
                (
                    b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /" + name + b" "
                    b"/CIDSystemInfo 5 0 R /DW 1000 /W " + w_array + b" /FontDescriptor 6 0 R >>"
                ),
                b"<< /Registry (Adobe) /Ordering (Identity) /Supplement 0 >>",
                (
                    b"<< /Type /FontDescriptor /FontName /" + name + b" /Flags " + str(desc["flags"]).encode("ascii")
                    + b" /FontBBox [" + bbox + b"] /ItalicAngle 0 /Ascent " + str(desc["ascent"]).encode("ascii")
                    + b" /Descent " + str(desc["descent"]).encode("ascii")
                    + b" /CapHeight " + str(desc["capHeight"]).encode("ascii")
                    + b" /StemV " + str(desc["stemV"]).encode("ascii")
                    + b" /FontFile2 7 0 R >>"
                ),
            ]
            ttf = font["ttf_bytes"]
            objects.append(
                b"<< /Length1 " + str(len(ttf)).encode("ascii") + b" /Length " + str(len(ttf)).encode("ascii")
                + b" >>\nstream\n" + ttf + b"\nendstream"
            )
        page_object_ids = self._pdf_page_object_ids(page_count, font)
        for page_object_id, content_object_id, stream in zip(page_object_ids, content_object_ids, streams):
            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PDF_PAGE_WIDTH} {PDF_PAGE_HEIGHT}] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_id} 0 R >>"
                ).encode("ascii")
            )
            objects.append(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            )
        return objects

    def _pdf_page_object_ids(self, page_count: int, font: dict[str, Any] | None) -> list[int]:
        first_page_id = 8 if font is not None else 6
        return [first_page_id + index * 2 for index in range(page_count)]

    def _pdf_content_object_ids(self, page_count: int, font: dict[str, Any] | None) -> list[int]:
        return [page_id + 1 for page_id in self._pdf_page_object_ids(page_count, font)]

    def _pdf_w_array_bytes(self, widths: dict[int, int]) -> bytes:
        if not widths:
            return b"[]"
        max_gid = max(widths)
        ordered = [widths.get(gid, 0) for gid in range(max_gid + 1)]
        body = " ".join(str(w) for w in ordered).encode("ascii")
        return b"[0 " + str(max_gid).encode("ascii") + b" [" + body + b"]]"

    def _build_embedded_font(self, text: str) -> dict[str, Any] | None:
        try:
            from fontTools.subset import Options, Subsetter
            from fontTools.ttLib import TTFont
        except ImportError:
            return None
        try:
            font = TTFont(PDF_CJK_FONT_PATH, fontNumber=0)
        except Exception:
            return None
        cmap = font.getBestCmap()
        cp_to_name: dict[int, str] = {}
        for char in text:
            cp = ord(char)
            if cp in cmap and cp not in cp_to_name:
                cp_to_name[cp] = cmap[cp]
        glyph_names = sorted(set(cp_to_name.values()) | {font.getGlyphName(0)})
        options = Options(layout_features=["*"], notdef_outline=True, name_IDs=[1, 2, 4, 5, 6], drop_tables=["BDF", "FFTM"])
        subsetter = Subsetter(options=options)
        subsetter.populate(glyphs=glyph_names)
        subsetter.subset(font)
        buffer = io.BytesIO()
        font.save(buffer)
        ttf_bytes = buffer.getvalue()
        glyph_order = font.getGlyphOrder()
        name_to_gid = {name: gid for gid, name in enumerate(glyph_order)}
        units = font["head"].unitsPerEm
        cid_map = {cp: name_to_gid[name] for cp, name in cp_to_name.items() if name in name_to_gid}
        widths = {gid: round(font["hmtx"][name][0] / units * 1000) for gid, name in enumerate(glyph_order)}
        head = font["head"]
        hhea = font["hhea"]
        scale = 1000 / units
        desc = {
            "flags": 4,
            "ascent": round(hhea.ascender * scale),
            "descent": round(hhea.descender * scale),
            "bbox": [round(head.xMin * scale), round(head.yMin * scale), round(head.xMax * scale), round(head.yMax * scale)],
            "capHeight": round(hhea.ascender * scale),
            "stemV": 80,
        }
        return {"ttf_bytes": ttf_bytes, "cid_map": cid_map, "widths": widths, "desc": desc}

    def _embedded_char_width_pt(self, char: str, font: dict[str, Any]) -> float:
        gid = font["cid_map"].get(ord(char))
        if gid is None:
            return float(self._pdf_char_width_pt(char))
        return font["widths"][gid] / 100.0

    def _pdf_identity_hex(self, value: str, cid_map: dict[int, int]) -> str:
        return "".join(f"{cid_map.get(ord(char), 0):04X}" for char in value)

    def _build_pdf_items(self, report: dict[str, Any]) -> list[_PdfItem]:
        conclusion = report["conclusion"]
        priority_color = PDF_COLOR_DANGER if conclusion["priority"] == "优先处置" else PDF_COLOR_BODY
        items: list[_PdfItem] = [
            _PdfItem("text", str(report["title"]), PDF_FONT_TITLE, PDF_COLOR_TITLE, 0, 26),
            _PdfItem("text", str(report["summary"]), PDF_FONT_FULL, PDF_COLOR_MUTED, 0, 18),
            _PdfItem(
                "text",
                f"报告编号：{report['report_id']}    巡检编号：{report['inspection_id']}",
                PDF_FONT_FOOTER,
                PDF_COLOR_MUTED,
            ),
            _PdfItem("rule", height=10),
            _PdfItem("text", "一、巡检结论", PDF_FONT_HEADING, PDF_COLOR_HEADING, 0, 22),
            _PdfItem("text", f"{conclusion['priority']}：{conclusion['finding']}", PDF_FONT_FULL, priority_color),
            _PdfItem("text", conclusion["action"]),
            _PdfItem("text", conclusion["alarmSummary"], color=PDF_COLOR_MUTED),
            _PdfItem(
                "text",
                f"最高风险：{report['highestRiskLabel']}    故障：{report['faultCount']}    "
                f"告警：{report['alarmCount']}    高风险及以上：{report['highRiskCount']}",
            ),
            _PdfItem("spacer", height=8),
            _PdfItem("text", "二、巡检对象", PDF_FONT_HEADING, PDF_COLOR_HEADING, 0, 22),
            _PdfItem("text", f"设备：{report['deviceName']}"),
            _PdfItem("text", f"位置：{report['location']}"),
            _PdfItem(
                "text",
                f"开始时间：{self._report_time(report['startedAt'])}    "
                f"结束时间：{self._report_time(report['endedAt'])}",
            ),
            _PdfItem("spacer", height=8),
            _PdfItem("text", "三、故障发现与处置建议", PDF_FONT_HEADING, PDF_COLOR_HEADING, 0, 22),
        ]
        if not report["faults"]:
            items.append(_PdfItem("text", "本次巡检未发现故障。", PDF_FONT_FULL, PDF_COLOR_MUTED))
        for index, fault in enumerate(report["faults"]):
            if index > 0:
                items.append(_PdfItem("rule", height=10))
            items.extend(self._pdf_fault_items(fault))
        return items

    def _pdf_fault_items(self, fault: dict[str, Any]) -> list[_PdfItem]:
        items: list[_PdfItem] = [
            _PdfItem("text", fault["title"], PDF_FONT_HEADING, PDF_COLOR_HEADING, 0, 22),
            _PdfItem(
                "text",
                f"发现情况：识别到{fault['faultTypeLabel']}，风险等级为{fault['riskLabel']}，"
                f"模型置信度 {fault['confidence']:.0%}。",
            ),
            _PdfItem("text", f"累计出现 {fault['occurrenceCount']} 次，证据帧参考：{fault['bestFrameId']}"),
            _PdfItem(
                "text",
                f"告警与状态：{fault['alarmMessage']} / 告警状态：{fault['alarmStatusLabel']} / "
                f"故障状态：{fault['processStatusLabel']}",
            ),
            _PdfItem(
                "text",
                f"状态跟踪：最近处理人 {fault['lastHandledBy']}，"
                f"最近处理时间 {self._report_time(fault['lastHandledAt'])}",
                color=PDF_COLOR_MUTED,
            ),
        ]
        advice = fault["advice"]
        if not advice:
            items.append(_PdfItem("text", "维修建议：尚未生成", PDF_FONT_FULL, PDF_COLOR_MUTED))
            return items
        items.extend(
            [
                _PdfItem("text", f"风险分析：{advice['riskAnalysis']}"),
                _PdfItem("text", "检查步骤：" + "；".join(advice["inspectionSteps"])),
                _PdfItem("text", "维修建议：" + "；".join(advice["maintenanceSuggestions"])),
                _PdfItem("text", "安全注意事项：" + "；".join(advice["safetyNotes"])),
            ]
        )
        advice_meta = [value for key in ("modelName", "adviceStatusLabel") if (value := advice.get(key))]
        if advice_meta:
            items.append(_PdfItem("text", "建议来源：" + " / ".join(advice_meta), PDF_FONT_FOOTER, PDF_COLOR_MUTED))
        return items

    def _layout_pdf_pages(
        self,
        items: list[_PdfItem],
        *,
        char_width_pt: "Callable[[str], float] | None" = None,
    ) -> list[list[_PdfItem]]:
        if char_width_pt is None:
            char_width_pt = self._pdf_char_width_pt
        pages: list[list[_PdfItem]] = [[]]
        used = 0
        available = PDF_TOP_MARGIN - PDF_FOOTER_Y - 24
        for item in items:
            pieces: list[_PdfItem] = []
            if item.kind == "text":
                budget = PDF_WRAP_BUDGET_PT - item.indent
                for wrapped in self._wrap_pdf_text(item.text, budget, char_width_pt=char_width_pt):
                    pieces.append(_PdfItem("text", wrapped, item.size, item.color, item.indent, item.height))
            else:
                pieces.append(item)
            for piece in pieces:
                if piece.kind in {"rule", "spacer"} and not pages[-1]:
                    continue
                if used and used + piece.height > available:
                    pages.append([])
                    used = 0
                    if piece.kind in {"rule", "spacer"}:
                        continue
                pages[-1].append(piece)
                used += piece.height
        return pages

    def _pdf_page_stream(
        self,
        items: list[_PdfItem],
        *,
        page_no: int,
        total_pages: int,
        report_id: str,
        glyph_hex: "Callable[[str], str] | None" = None,
    ) -> bytes:
        if glyph_hex is None:
            glyph_hex = self._pdf_hex_text
        ops: list[str] = []
        y = PDF_TOP_MARGIN
        for item in items:
            if item.kind == "spacer":
                y -= item.height
                continue
            if item.kind == "rule":
                r, g, b = PDF_COLOR_RULE
                x = PDF_LEFT_MARGIN + item.indent
                ops.append(
                    f"{r:.3f} {g:.3f} {b:.3f} RG 1 w "
                    f"{x:.2f} {y - item.height / 2:.2f} {PDF_PRINTABLE_WIDTH - item.indent:.2f} 0 re S "
                    f"0 0 0 RG"
                )
                y -= item.height
                continue
            r, g, b = item.color
            x = PDF_LEFT_MARGIN + item.indent
            baseline = y - item.size
            ops.append(
                f"BT {r:.3f} {g:.3f} {b:.3f} rg /F1 {item.size} Tf "
                f"1 0 0 1 {x:.2f} {baseline:.2f} Tm <{glyph_hex(item.text)}> Tj ET"
            )
            y -= item.height
        footer = f"{report_id}  ·  第 {page_no} 页 / 共 {total_pages} 页"
        r, g, b = PDF_COLOR_MUTED
        ops.append(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg /F1 {PDF_FONT_FOOTER} Tf "
            f"1 0 0 1 {PDF_LEFT_MARGIN:.2f} {PDF_FOOTER_Y:.2f} Tm <{glyph_hex(footer)}> Tj ET"
        )
        return "\n".join(ops).encode("ascii")

    def _wrap_pdf_text(
        self,
        value: str,
        budget: int = PDF_WRAP_BUDGET_PT,
        *,
        char_width_pt: "Callable[[str], float] | None" = None,
    ) -> list[str]:
        if char_width_pt is None:
            char_width_pt = self._pdf_char_width_pt
        if value == "":
            return [""]
        lines: list[str] = []
        for segment in value.split("\n"):
            if not segment:
                lines.append("")
                continue
            line = ""
            line_pt = 0.0
            for char in segment:
                char_pt = char_width_pt(char)
                if line and line_pt + char_pt > budget:
                    lines.append(line)
                    line = ""
                    line_pt = 0.0
                    if char == " ":
                        continue
                line += char
                line_pt += char_pt
            if line:
                lines.append(line)
        return lines or [""]

    def _pdf_char_width_pt(self, char: str) -> int:
        return 5 if ord(char) < 128 else 10

    def _pdf_text_width_pt(self, value: str) -> int:
        return sum(self._pdf_char_width_pt(char) for char in value)

    def _pdf_hex_text(self, value: str) -> str:
        return value.encode("utf-16-be").hex().upper()

    def _fault_display_name(self, fault: sqlite3.Row | None) -> str:
        if fault is None:
            return "设备"
        return FAULT_LABELS.get(fault["fault_type"], fault["fault_type"])

    def _device_display_name(self, device: sqlite3.Row) -> str:
        return DEVICE_NAME_LABELS.get(device["device_id"], device["device_name"])

    def _location_display_name(self, location: str) -> str:
        return DEVICE_LOCATION_LABELS.get(location, location)

    def _highest_risk_level(self, faults: list[sqlite3.Row]) -> str:
        if not faults:
            return "none"
        return max((fault["risk_level"] for fault in faults), key=lambda value: RISK_ORDER.get(value, 0))

    def _primary_fault(self, faults: list[sqlite3.Row]) -> sqlite3.Row | None:
        if not faults:
            return None
        return max(
            faults,
            key=lambda fault: (RISK_ORDER.get(fault["risk_level"], 0), fault["last_seen_at"]),
        )

    def _report_conclusion(
        self,
        *,
        fault_count: int,
        alarm_count: int,
        high_risk_count: int,
        highest_risk: str,
    ) -> dict[str, str]:
        highest_risk_label = RISK_LABELS.get(highest_risk, highest_risk)
        if fault_count == 0:
            finding = "本次巡检未发现故障或告警，设备状态可继续观察。"
            priority = "常规巡检"
            action = "按既定周期继续巡检，并保留本次结果作为后续比对基线。"
        elif highest_risk in {"critical", "high"}:
            finding = f"本次巡检发现 {fault_count} 项故障，最高风险等级为{highest_risk_label}。"
            priority = "优先处置"
            action = "建议尽快安排现场复核，必要时执行停电、隔离和专项检修流程。"
        else:
            finding = f"本次巡检发现 {fault_count} 项故障，最高风险等级为{highest_risk_label}。"
            priority = "计划处理"
            action = "建议纳入近期运维计划，先完成证据复核和现场确认，再按规程处理。"
        return {
            "finding": finding,
            "priority": priority,
            "action": action,
            "alarmSummary": f"触发 {alarm_count} 条告警，其中高风险及以上 {high_risk_count} 项。",
        }

    def _report_advice_section(self, advice: sqlite3.Row) -> dict[str, Any]:
        return {
            "riskAnalysis": advice["risk_analysis"],
            "inspectionSteps": _json_load(advice["inspection_steps_json"], []),
            "maintenanceSuggestions": _json_load(advice["maintenance_suggestions_json"], []),
            "safetyNotes": _json_load(advice["safety_notes_json"], []),
            "modelName": advice["model_name"],
            "adviceStatus": advice["advice_status"],
            "adviceStatusLabel": ADVICE_STATUS_LABELS.get(advice["advice_status"], advice["advice_status"]),
        }

    def _report_time(self, value: str | None) -> str:
        if not value:
            return "未记录"
        parsed = _dt(value)
        if parsed is None:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")

    def _html_fault_section(self, fault: dict[str, Any]) -> str:
        advice = fault["advice"]
        advice_html = (
            self._html_advice_section(advice)
            if advice
            else "<p>该故障尚未生成维修建议。</p>"
        )
        return (
            "<section class=\"section\">"
            f"<h2>{html_lib.escape(fault['title'])}</h2>"
            "<h3>发现情况</h3>"
            f"<p>系统在本次巡检中识别到{html_lib.escape(fault['faultTypeLabel'])}，风险等级为{html_lib.escape(fault['riskLabel'])}，模型置信度 {fault['confidence']:.0%}。</p>"
            f"<p>累计出现 {fault['occurrenceCount']} 次，最佳证据帧为 {html_lib.escape(fault['bestFrameId'])}。</p>"
            f"<p class=\"evidence\">证据图：{html_lib.escape(fault['bestImageUrl'])}</p>"
            "<h3>告警与状态</h3>"
            f"<p>告警：{html_lib.escape(fault['alarmMessage'])} / 告警状态：{html_lib.escape(fault['alarmStatusLabel'])}</p>"
            f"<p>故障状态：{html_lib.escape(fault['processStatusLabel'])} / 最近处理人：{html_lib.escape(fault['lastHandledBy'])} / 最近处理时间：{html_lib.escape(self._report_time(fault['lastHandledAt']))}</p>"
            f"{advice_html}"
            "</section>"
        )

    def _html_advice_section(self, advice: dict[str, Any]) -> str:
        return (
            "<h3>风险分析</h3>"
            f"<p>{html_lib.escape(advice['riskAnalysis'])}</p>"
            f"<h3>检查步骤</h3>{self._html_list(advice['inspectionSteps'])}"
            f"<h3>维修建议</h3>{self._html_list(advice['maintenanceSuggestions'])}"
            f"<h3>安全注意事项</h3>{self._html_list(advice['safetyNotes'])}"
            f"<p class=\"meta\">建议来源：{html_lib.escape(advice['modelName'])} / 生成状态：{html_lib.escape(advice['adviceStatusLabel'])}</p>"
        )

    def _html_list(self, items: list[str]) -> str:
        if not items:
            return "<p>暂无。</p>"
        return "<ul>" + "".join(f"<li>{html_lib.escape(item)}</li>" for item in items) + "</ul>"

    def _ensure_device(self, connection: sqlite3.Connection, device_id: str, now: datetime) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if row is not None:
            return row
        connection.execute(
            """
            INSERT INTO devices (
                device_id, device_name, device_type, location, status, created_at, updated_at
            )
            VALUES (?, ?, 'unknown', 'unknown', 'unknown', ?, ?)
            """,
            (device_id, device_id, _iso(now), _iso(now)),
        )
        return connection.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()

    def _get_inspection_row(self, connection: sqlite3.Connection, inspection_id: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM inspections WHERE inspection_id = ?",
            (inspection_id,),
        ).fetchone()

    def _next_id(self, connection: sqlite3.Connection, table: str, column: str, prefix: str) -> str:
        count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] + 1
        return f"{prefix}-{count:06d}"

    def _next_dated_id(self, connection: sqlite3.Connection, table: str, column: str, prefix: str) -> str:
        today = current_timestamp().strftime("%Y%m%d")
        count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] + 1
        return f"{prefix}-{today}-{count:04d}"

    def _next_report_id(self, connection: sqlite3.Connection, generated_at: datetime) -> str:
        count = connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] + 1
        return f"report-{generated_at.strftime('%Y%m%d')}-{count:04d}"

    def _next_report_version(self, connection: sqlite3.Connection, inspection_id: str) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM reports WHERE inspection_id = ? AND format = 'html'",
            (inspection_id,),
        ).fetchone()
        return int(row[0])

    def _enrich_detections(self, result_id: str, payload: DetectionUploadRequest) -> list[Detection]:
        enriched = []
        for index, detection in enumerate(payload.detections, start=1):
            data = detection.model_dump()
            data["detectionId"] = data["detectionId"] or f"{result_id}-detection-{index:03d}"
            data["imageWidth"] = data["imageWidth"] or payload.imageWidth
            data["imageHeight"] = data["imageHeight"] or payload.imageHeight
            enriched.append(Detection(**data))
        return enriched

    def _classify_fault(self, fault_type: str, confidence: float) -> tuple[str, str, str]:
        if confidence < 0.5:
            return "low", "info", "P3"
        if fault_type == "fire":
            return "critical", "critical", "P0"
        if fault_type in {"smoke", "person_intrusion", "helmet_missing", "surface_damage"}:
            return "high", "warning", "P1"
        if fault_type in {"rust", "foreign_object"}:
            return "medium", "warning", "P2"
        return "low", "info", "P3"

    def _alarm_message(self, fault_type: str, risk_level: str) -> str:
        fault_label = FAULT_LABELS.get(fault_type, fault_type)
        risk_label = RISK_LABELS.get(risk_level, risk_level)
        return f"检测到{fault_label}，{risk_label}"

    def _rule_template_advice(self, fault: sqlite3.Row) -> dict[str, Any]:
        fault_type = fault["fault_type"]
        fault_label = FAULT_LABELS.get(fault_type, fault_type)
        risk_label = RISK_LABELS.get(fault["risk_level"], fault["risk_level"])
        base = {
            "possibleCauses": ["设备长期运行老化", "外力冲击或机械振动", "潮湿、污秽或高温等环境影响"],
            "riskAnalysis": f"检测到{fault_label}，当前风险等级为{risk_label}。该问题可能影响设备运行稳定性，建议尽快安排人工复核。",
            "inspectionSteps": [
                "核对最佳证据帧及相邻帧，确认故障位置和范围。",
                "在满足安全隔离条件后，对现场设备外观、连接点和周边环境进行复核。",
                "记录故障是否扩大、是否伴随异响、异味、放电痕迹或温升异常。",
            ],
            "maintenanceSuggestions": [
                "安排具备资质的运维人员进行现场复检。",
                "若现场确认故障存在，应根据设备规程修复或更换受影响部件。",
            ],
            "safetyNotes": [
                "现场操作前确认设备处于安全状态，并执行必要的停电、验电和隔离措施。",
                "系统生成的建议仅作为辅助判断，最终处置需由现场负责人复核确认。",
            ],
        }
        if fault_type in {"smoke", "fire"}:
            base["possibleCauses"] = ["设备过热", "短路或接触不良", "周边存在易燃物或散热条件不足"]
            base["maintenanceSuggestions"] = [
                "立即升级为紧急处置流程并通知现场值守人员。",
                "按现场安全规程隔离电源，确认无持续燃烧、烟雾或二次风险后再开展复核。",
            ]
        return base

    def _generate_advice_payload(self, fault: sqlite3.Row) -> tuple[dict[str, Any], str, str]:
        api_url, model_name, provider = _resolve_llm_provider_config()
        if not api_url or not settings.llm_api_key or provider == "rule-template":
            return self._rule_template_advice(fault), "rule-template", "fallback"

        for _ in range(max(settings.llm_max_retries, 1)):
            try:
                return self._call_llm_provider(fault, api_url=api_url, model_name=model_name), model_name, "ready"
            except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
                _ = exc
        fallback = self._rule_template_advice(fault)
        fallback["riskAnalysis"] = (
            f"{fallback['riskAnalysis']} 大模型服务暂不可用，已采用规则模板生成本建议。"
        )
        return fallback, "rule-template", "fallback"

    def _call_llm_provider(self, fault: sqlite3.Row, *, api_url: str, model_name: str) -> dict[str, Any]:
        body = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电力设备智能巡检维修建议助手。请只返回 json 对象，不要返回 Markdown。"
                        "JSON 必须包含 possibleCauses、riskAnalysis、inspectionSteps、maintenanceSuggestions、safetyNotes。"
                        "所有字段值必须使用中文，列表项要面向现场运维人员，表达简洁可执行。"
                        "示例：{\"possibleCauses\":[\"原因\"],\"riskAnalysis\":\"风险分析\","
                        "\"inspectionSteps\":[\"步骤\"],\"maintenanceSuggestions\":[\"建议\"],"
                        "\"safetyNotes\":[\"注意事项\"]}。"
                    ),
                },
                {
                    "role": "user",
                    "content": _json_dump(
                        {
                            "deviceType": fault["device_type"],
                            "faultType": fault["fault_type"],
                            "faultTypeLabel": FAULT_LABELS.get(fault["fault_type"], fault["fault_type"]),
                            "confidence": fault["confidence"],
                            "riskLevel": fault["risk_level"],
                            "riskLevelLabel": RISK_LABELS.get(fault["risk_level"], fault["risk_level"]),
                            "location": fault["location"],
                            "bestImageUrl": fault["best_annotated_image_url"] or fault["best_image_url"],
                        }
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            api_url,
            data=_json_dump(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            provider_payload = json.loads(response.read().decode("utf-8"))
        content = provider_payload["choices"][0]["message"]["content"]
        return self._parse_advice_content(content)

    def _parse_advice_content(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        payload = json.loads(cleaned)
        required_list_fields = [
            "possibleCauses",
            "inspectionSteps",
            "maintenanceSuggestions",
            "safetyNotes",
        ]
        for field in required_list_fields:
            if not isinstance(payload.get(field), list) or not all(
                isinstance(item, str) for item in payload[field]
            ):
                raise ValueError(f"invalid advice field: {field}")
        if not isinstance(payload.get("riskAnalysis"), str):
            raise ValueError("invalid advice field: riskAnalysis")
        return {
            "possibleCauses": payload["possibleCauses"],
            "riskAnalysis": payload["riskAnalysis"],
            "inspectionSteps": payload["inspectionSteps"],
            "maintenanceSuggestions": payload["maintenanceSuggestions"],
            "safetyNotes": payload["safetyNotes"],
        }

    def _upload_result_from_row(self, row: sqlite3.Row, *, duplicate: bool) -> DetectionUploadResult:
        inspection_status = "running"
        with self.store.connect() as connection:
            inspection = self._get_inspection_row(connection, row["inspection_id"])
            if inspection is not None:
                inspection_status = inspection["status"]
        return DetectionUploadResult(
            resultId=row["result_id"],
            inspectionId=row["inspection_id"],
            frameId=row["frame_id"],
            accepted=True,
            duplicate=duplicate,
            processedAt=_dt(row["processed_at"]),
            inspectionStatus=inspection_status,
            faultsCreated=0 if duplicate else row["faults_created"],
            faultsUpdated=0 if duplicate else row["faults_updated"],
            alarmsCreated=0 if duplicate else row["alarms_created"],
            alarmsSuppressed=0 if duplicate else row["alarms_suppressed"],
            reportTriggered=bool(row["report_triggered"]),
            warnings=_json_load(row["warnings_json"], []),
        )

    def _where_clause(self, filters: list[tuple[str, Any | None]]) -> tuple[str, list[Any]]:
        parts = []
        params = []
        for condition, value in filters:
            if value is not None:
                parts.append(condition)
                params.append(value)
        return (f"WHERE {' AND '.join(parts)}" if parts else "", params)

    def _device_from_row(self, row: sqlite3.Row) -> Device:
        return Device(
            deviceId=row["device_id"],
            deviceName=row["device_name"],
            deviceType=row["device_type"],
            location=row["location"],
            status=row["status"],
            createdAt=_dt(row["created_at"]),
            updatedAt=_dt(row["updated_at"]),
        )

    def _inspection_item_from_row(self, row: sqlite3.Row) -> InspectionListItem:
        return InspectionListItem(
            inspectionId=row["inspection_id"],
            deviceId=row["device_id"],
            deviceName=row["device_name"],
            status=row["status"],
            startedAt=_dt(row["started_at"]),
            endedAt=_dt(row["ended_at"]),
            faultCount=row["fault_count"],
            alarmCount=row["alarm_count"],
        )

    def _fault_from_row(self, row: sqlite3.Row) -> Any:
        from app.models.inspection import Fault

        return Fault(
            faultId=row["fault_id"],
            inspectionId=row["inspection_id"],
            deviceId=row["device_id"],
            deviceType=row["device_type"],
            faultType=row["fault_type"],
            confidence=row["confidence"],
            riskLevel=row["risk_level"],
            alarmRequired=bool(row["alarm_required"]),
            alarmLevel=row["alarm_level"],
            priority=row["priority"],
            processStatus=row["process_status"],
            eventKey=row["event_key"],
            eventStatus=row["event_status"],
            firstSeenAt=_dt(row["first_seen_at"]),
            lastSeenAt=_dt(row["last_seen_at"]),
            occurrenceCount=row["occurrence_count"],
            lastConfidence=row["last_confidence"],
            maxConfidence=row["max_confidence"],
            bestFrameId=row["best_frame_id"],
            bestImageUrl=row["best_image_url"],
            bestAnnotatedImageUrl=row["best_annotated_image_url"],
            location=row["location"],
            createdAt=_dt(row["created_at"]),
            lastHandledBy=row["last_handled_by"],
            lastHandledAt=_dt(row["last_handled_at"]),
            lastHandleNote=row["last_handle_note"],
        )

    def _alarm_from_row(self, row: sqlite3.Row) -> Alarm:
        return Alarm(
            alarmId=row["alarm_id"],
            faultId=row["fault_id"],
            deviceId=row["device_id"],
            alarmLevel=row["alarm_level"],
            riskLevel=row["risk_level"],
            message=row["message"],
            processStatus=row["process_status"],
            dedupKey=row["dedup_key"],
            firstTriggeredAt=_dt(row["first_triggered_at"]),
            lastTriggeredAt=_dt(row["last_triggered_at"]),
            suppressedCount=row["suppressed_count"],
            reopenCount=row["reopen_count"],
            createdAt=_dt(row["created_at"]),
            lastHandledBy=row["last_handled_by"],
            lastHandledAt=_dt(row["last_handled_at"]),
            lastHandleNote=row["last_handle_note"],
        )

    def _event_from_row(self, row: sqlite3.Row) -> EventItem:
        return EventItem(
            eventId=f"event-{row['fault_id'].split('-')[-1]}",
            eventType="fault",
            inspectionId=row["inspection_id"],
            deviceId=row["device_id"],
            deviceName=row["device_name"],
            faultId=row["fault_id"],
            alarmId=row["alarm_id"],
            faultType=row["fault_type"],
            riskLevel=row["risk_level"],
            alarmLevel=row["alarm_level"],
            processStatus=row["process_status"],
            title=self._alarm_message(row["fault_type"], row["risk_level"]),
            summary=f"累计检测 {row['occurrence_count']} 次，最佳证据帧：{row['best_frame_id']}。",
            occurrenceCount=row["occurrence_count"],
            firstOccurredAt=_dt(row["first_seen_at"]),
            lastOccurredAt=_dt(row["last_seen_at"]),
            latestFrameId=row["best_frame_id"],
            latestImageUrl=row["best_annotated_image_url"] or row["best_image_url"],
            adviceStatus=row["advice_status"],
            lastHandledBy=row["last_handled_by"],
            lastHandledAt=_dt(row["last_handled_at"]),
            lastHandleNote=row["last_handle_note"],
        )

    def _advice_from_row(self, row: sqlite3.Row) -> Advice:
        return Advice(
            adviceId=row["advice_id"],
            faultId=row["fault_id"],
            possibleCauses=_json_load(row["possible_causes_json"], []),
            riskAnalysis=row["risk_analysis"],
            inspectionSteps=_json_load(row["inspection_steps_json"], []),
            maintenanceSuggestions=_json_load(row["maintenance_suggestions_json"], []),
            safetyNotes=_json_load(row["safety_notes_json"], []),
            modelName=row["model_name"],
            adviceStatus=row["advice_status"],
            createdAt=_dt(row["created_at"]),
        )

    def _report_list_item_from_row(self, row: sqlite3.Row) -> ReportListItem:
        return ReportListItem(
            reportId=row["report_id"],
            inspectionId=row["inspection_id"],
            title=row["title"],
            reportStatus=row["report_status"],
            createdAt=_dt(row["created_at"]),
            format=row["format"],
            url=row["url"],
        )

    def _high_risk_alarm_from_row(self, row: sqlite3.Row) -> HighRiskAlarm:
        return HighRiskAlarm(
            alarmId=row["alarm_id"],
            faultId=row["fault_id"],
            inspectionId=row["inspection_id"],
            deviceId=row["device_id"],
            deviceName=row["device_name"],
            faultType=row["fault_type"],
            riskLevel=row["risk_level"],
            alarmLevel=row["alarm_level"],
            processStatus=row["process_status"],
            createdAt=_dt(row["created_at"]),
        )


_service: InspectionService | None = None


def get_service() -> InspectionService:
    global _service
    if _service is None:
        _service = InspectionService(SQLiteStore(settings.database_path))
    return _service


def reset_service_for_tests(database_path: str) -> InspectionService:
    global _service
    path = Path(database_path)
    if path.exists():
        path.unlink()
    _service = InspectionService(SQLiteStore(database_path))
    return _service
