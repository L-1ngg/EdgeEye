from __future__ import annotations

import hashlib
import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '[]')
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
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ApiException(
                    "DUPLICATE_UPLOAD",
                    "inspection frame already has a saved detection result",
                    status_code=409,
                    details={"inspectionId": payload.inspectionId, "frameId": payload.frameId},
                ) from exc

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
            generated_at = current_timestamp()
            file_name = f"{report_id}.{report_format}"
            download_url = f"/reports/{file_name}"
            if report_format == "pdf":
                self._write_pdf_report(report, file_name)
            else:
                self._write_html_report(report, file_name)
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
        event_key = payload.eventKey or f"{payload.inspectionId}:{device_id}:{fault_type}"
        event_status = "resolved" if payload.uploadReason == "fault_resolved" else "ongoing"
        existing = connection.execute("SELECT * FROM faults WHERE event_key = ?", (event_key,)).fetchone()
        if existing is None:
            fault_id = self._next_id(connection, "faults", "fault_id", "fault")
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
                "resolved" if event_status == "resolved" else existing["process_status"],
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

    def _generate_report(self, connection: sqlite3.Connection, inspection_id: str, generated_at: datetime) -> None:
        existing = connection.execute(
            "SELECT * FROM reports WHERE inspection_id = ? AND format = 'html' AND version = 1",
            (inspection_id,),
        ).fetchone()
        fault_count = connection.execute(
            "SELECT COUNT(*) FROM faults WHERE inspection_id = ?",
            (inspection_id,),
        ).fetchone()[0]
        alarm_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM alarms a
            JOIN faults f ON f.fault_id = a.fault_id
            WHERE f.inspection_id = ?
            """,
            (inspection_id,),
        ).fetchone()[0]
        inspection = self._get_inspection_row(connection, inspection_id)
        device = connection.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (inspection["device_id"],),
        ).fetchone()
        title = f"{device['device_name']} inspection report"
        summary = f"Inspection {inspection_id} completed with {fault_count} fault(s) and {alarm_count} alarm(s)."
        report_id = existing["report_id"] if existing else self._next_report_id(connection, generated_at)
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
            self._write_html_report({"report_id": report_id, "title": title, "summary": summary}, f"{report_id}.html")
            return
        connection.execute(
            """
            INSERT INTO reports (
                report_id, inspection_id, title, summary, report_status, format, url, created_at, exports_json, version
            )
            VALUES (?, ?, ?, ?, 'ready', 'html', ?, ?, ?, 1)
            """,
            (report_id, inspection_id, title, summary, url, _iso(generated_at), _json_dump(exports)),
        )
        self._write_html_report({"report_id": report_id, "title": title, "summary": summary}, f"{report_id}.html")

    def _reports_dir(self) -> Path:
        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir

    def _write_html_report(self, report: sqlite3.Row | dict[str, Any], file_name: str) -> None:
        title = report["title"]
        summary = report["summary"]
        html = (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{title}</title></head><body>"
            f"<h1>{title}</h1><p>{summary}</p>"
            f"<p>Report ID: {report['report_id']}</p>"
            "</body></html>"
        )
        (self._reports_dir() / file_name).write_text(html, encoding="utf-8")

    def _write_pdf_report(self, report: sqlite3.Row | dict[str, Any], file_name: str) -> None:
        title = str(report["title"])
        summary = str(report["summary"])
        lines = [title, summary, f"Report ID: {report['report_id']}"]
        text_commands = ["BT", "/F1 14 Tf", "72 760 Td"]
        for index, line in enumerate(lines):
            if index:
                text_commands.append("0 -24 Td")
            text_commands.append(f"({self._escape_pdf_text(line)}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("latin-1", errors="replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
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

    def _escape_pdf_text(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

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
        labels = {
            "surface_damage": "surface damage detected",
            "rust": "rust detected",
            "foreign_object": "foreign object detected",
            "smoke": "smoke detected",
            "fire": "fire detected",
            "person_intrusion": "person intrusion detected",
            "helmet_missing": "helmet missing detected",
            "unknown": "unknown fault detected",
        }
        return f"{labels.get(fault_type, 'fault detected')} with {risk_level} risk"

    def _rule_template_advice(self, fault: sqlite3.Row) -> dict[str, Any]:
        fault_type = fault["fault_type"]
        base = {
            "possibleCauses": ["equipment aging", "external impact", "environmental exposure"],
            "riskAnalysis": f"{fault_type} is classified as {fault['risk_level']} risk and requires manual review.",
            "inspectionSteps": [
                "Verify the best evidence frame and nearby frames.",
                "Inspect the device area on site after safety isolation.",
                "Record whether the issue is expanding or stable.",
            ],
            "maintenanceSuggestions": [
                "Schedule a qualified technician for follow-up inspection.",
                "Repair or replace affected parts if the field check confirms the fault.",
            ],
            "safetyNotes": [
                "Confirm the equipment is in a safe operating state before maintenance.",
                "Treat generated advice as decision support that must be reviewed by staff.",
            ],
        }
        if fault_type in {"smoke", "fire"}:
            base["possibleCauses"] = ["overheating", "short circuit", "flammable material nearby"]
            base["maintenanceSuggestions"] = [
                "Escalate immediately to emergency response staff.",
                "Isolate power according to site safety procedures.",
            ]
        return base

    def _generate_advice_payload(self, fault: sqlite3.Row) -> tuple[dict[str, Any], str, str]:
        if not settings.llm_api_url or not settings.llm_api_key or settings.llm_provider == "rule-template":
            return self._rule_template_advice(fault), "rule-template", "fallback"

        last_error: Exception | None = None
        for _ in range(max(settings.llm_max_retries, 1)):
            try:
                return self._call_llm_provider(fault), settings.llm_model_name, "ready"
            except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
                last_error = exc
        fallback = self._rule_template_advice(fault)
        fallback["riskAnalysis"] = (
            f"{fallback['riskAnalysis']} LLM provider failed; fallback advice was generated locally."
        )
        if last_error is not None:
            fallback["riskAnalysis"] = f"{fallback['riskAnalysis']} Last error: {type(last_error).__name__}."
        return fallback, "rule-template", "fallback"

    def _call_llm_provider(self, fault: sqlite3.Row) -> dict[str, Any]:
        body = {
            "model": settings.llm_model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate electrical inspection repair advice. "
                        "Return JSON only with possibleCauses, riskAnalysis, "
                        "inspectionSteps, maintenanceSuggestions, and safetyNotes."
                    ),
                },
                {
                    "role": "user",
                    "content": _json_dump(
                        {
                            "deviceType": fault["device_type"],
                            "faultType": fault["fault_type"],
                            "confidence": fault["confidence"],
                            "riskLevel": fault["risk_level"],
                            "location": fault["location"],
                            "bestImageUrl": fault["best_annotated_image_url"] or fault["best_image_url"],
                        }
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            settings.llm_api_url,
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
            summary=f"Detected {row['occurrence_count']} time(s); best frame {row['best_frame_id']}.",
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
