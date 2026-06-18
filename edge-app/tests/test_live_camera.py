import unittest

from edge_app.live_camera import build_detection_payload, frame_id, raw_frame_url


class LiveCameraPayloadTest(unittest.TestCase):
    def test_frame_id_is_contract_shape(self) -> None:
        self.assertEqual(frame_id(1), "frame-000001")
        self.assertEqual(frame_id(42), "frame-000042")

    def test_raw_frame_url_matches_uploads_contract(self) -> None:
        self.assertEqual(
            raw_frame_url("inspection-20260618-0001", "frame-000001"),
            "/uploads/raw/inspection-20260618-0001/frame-000001.jpg",
        )

    def test_payload_uses_existing_detection_upload_contract(self) -> None:
        payload = build_detection_payload(
            inspection_id="inspection-20260618-0001",
            frame="frame-000001",
            frame_seq=1,
            timestamp="2026-06-18T21:00:00+08:00",
            device_id="device-001",
            image_url="/uploads/raw/inspection-20260618-0001/frame-000001.jpg",
            image_width=640,
            image_height=480,
            latency_ms=12.345,
            fps=1.2,
            cpu_usage=10.0,
            memory_usage=20.0,
        )

        self.assertEqual(payload["idempotencyKey"], "inspection-20260618-0001:frame-000001")
        self.assertEqual(payload["inspectionId"], "inspection-20260618-0001")
        self.assertEqual(payload["frameId"], "frame-000001")
        self.assertEqual(payload["uploadReason"], "periodic_sample")
        self.assertEqual(payload["imageWidth"], 640)
        self.assertEqual(payload["imageHeight"], 480)
        self.assertEqual(payload["detections"], [])
        self.assertIsNone(payload["annotatedImageUrl"])
        self.assertIsNone(payload["performance"]["npuUsage"])
        self.assertNotIn("faults", payload)


if __name__ == "__main__":
    unittest.main()
