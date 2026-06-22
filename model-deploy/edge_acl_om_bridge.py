#!/usr/bin/env python3
"""Run YOLO OM inference through pyACL and emit EdgeEye detections as JSON."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import acl
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - depends on Atlas runtime image.
    raise SystemExit(f"Missing runtime dependency for ACL OM inference: {exc}") from exc


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT_DIR / "models" / "artifacts" / "edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om"
DEFAULT_CLASSES = Path(__file__).resolve().parent / "classes-edgeeye-insulator-v1.json"
DEFAULT_PREPROCESS = Path(__file__).resolve().parent / "preprocess-edgeeye-insulator-v1.json"
DEFAULT_OUTPUT_SHAPE = (1, 6, 8400)
ACL_MEM_MALLOC_HUGE_FIRST = 2
ACL_MEMCPY_HOST_TO_DEVICE = 1
ACL_MEMCPY_DEVICE_TO_HOST = 2


def main() -> None:
    args = parse_args()
    helpers = load_onnx_bridge_helpers()
    class_map = helpers.load_classes(args.classes)
    preprocess = helpers.load_preprocess(args.preprocess)
    output_shape = parse_output_shape(args.output_shape)

    result = infer_image(
        model_path=args.model,
        image_path=args.image,
        class_map=class_map,
        preprocess=preprocess,
        output_shape=output_shape,
        device_id=args.device_id,
        helpers=helpers,
    )
    if args.annotated_output:
        helpers.save_annotated_image(args.image, args.annotated_output, result["detections"])
        result["annotatedImagePath"] = str(args.annotated_output)

    print(json.dumps(result, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Atlas ACL/OM inference for one image.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASSES)
    parser.add_argument("--preprocess", type=Path, default=DEFAULT_PREPROCESS)
    parser.add_argument("--annotated-output", type=Path)
    parser.add_argument("--device-id", type=int, default=0)
    parser.add_argument("--output-shape", default=",".join(str(item) for item in DEFAULT_OUTPUT_SHAPE))
    return parser.parse_args()


def load_onnx_bridge_helpers() -> Any:
    path = Path(__file__).resolve().with_name("edge_onnx_bridge.py")
    spec = importlib.util.spec_from_file_location("edge_onnx_bridge_helpers", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_output_shape(value: str) -> tuple[int, ...]:
    try:
        shape = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise SystemExit(f"Invalid --output-shape value: {value}") from exc
    if not shape or any(item <= 0 for item in shape):
        raise SystemExit(f"Invalid --output-shape value: {value}")
    return shape


def infer_image(
    *,
    model_path: Path,
    image_path: Path,
    class_map: dict[int, Any],
    preprocess: Any,
    output_shape: tuple[int, ...],
    device_id: int,
    helpers: Any,
) -> dict[str, Any]:
    if not model_path.exists():
        raise SystemExit(f"Model file not found: {model_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"Could not read image: {image_path}")

    image_height, image_width = image.shape[:2]
    model_input, scale, pad_x, pad_y = helpers.prepare_image(image, preprocess)
    output, latency_ms = AclOmSession(model_path, device_id).infer(model_input, output_shape)
    detections = helpers.parse_yolo_output(
        output,
        class_map=class_map,
        preprocess=preprocess,
        image_width=image_width,
        image_height=image_height,
        scale=scale,
        pad_x=pad_x,
        pad_y=pad_y,
    )
    return {
        "detections": detections,
        "imageWidth": image_width,
        "imageHeight": image_height,
        "latencyMs": round(latency_ms, 3),
        "fps": round(1000.0 / latency_ms, 3) if latency_ms > 0 else 0.0,
        "modelPath": str(model_path),
        "annotatedImagePath": None,
    }


class AclOmSession:
    def __init__(self, model_path: Path, device_id: int) -> None:
        self._model_path = model_path
        self._device_id = device_id

    def infer(self, model_input: np.ndarray, output_shape: tuple[int, ...]) -> tuple[np.ndarray, float]:
        initialized = False
        model_id: int | None = None
        desc = None
        try:
            check_ret(acl.init(), "acl.init")
            initialized = True
            check_ret(acl.rt.set_device(self._device_id), "acl.rt.set_device")
            model_id, ret = acl.mdl.load_from_file(str(self._model_path))
            check_ret(ret, "acl.mdl.load_from_file")
            desc = acl.mdl.create_desc()
            check_ret(acl.mdl.get_desc(desc, model_id), "acl.mdl.get_desc")
            output, latency_ms = self._execute(model_id, desc, np.ascontiguousarray(model_input), output_shape)
            return output, latency_ms
        finally:
            if desc is not None:
                acl.mdl.destroy_desc(desc)
            if model_id is not None:
                acl.mdl.unload(model_id)
            if initialized:
                acl.rt.reset_device(self._device_id)
                acl.finalize()

    def _execute(
        self,
        model_id: int,
        desc: Any,
        model_input: np.ndarray,
        output_shape: tuple[int, ...],
    ) -> tuple[np.ndarray, float]:
        input_size = int(checked_value(acl.mdl.get_input_size_by_index(desc, 0), "acl.mdl.get_input_size_by_index"))
        output_size = int(checked_value(acl.mdl.get_output_size_by_index(desc, 0), "acl.mdl.get_output_size_by_index"))
        expected_output_bytes = int(np.prod(output_shape)) * np.dtype(np.float32).itemsize
        if model_input.nbytes != input_size:
            raise RuntimeError(f"model input is {model_input.nbytes} bytes, expected {input_size}")
        if output_size != expected_output_bytes:
            raise RuntimeError(f"model output is {output_size} bytes, expected {expected_output_bytes}")

        input_ptr = None
        output_ptr = None
        input_dataset = None
        output_dataset = None
        try:
            input_ptr, ret = acl.rt.malloc(input_size, ACL_MEM_MALLOC_HUGE_FIRST)
            check_ret(ret, "acl.rt.malloc input")
            output_ptr, ret = acl.rt.malloc(output_size, ACL_MEM_MALLOC_HUGE_FIRST)
            check_ret(ret, "acl.rt.malloc output")
            check_ret(
                acl.rt.memcpy(
                    input_ptr,
                    input_size,
                    acl.util.numpy_to_ptr(model_input),
                    input_size,
                    ACL_MEMCPY_HOST_TO_DEVICE,
                ),
                "acl.rt.memcpy input",
            )

            input_dataset = create_dataset(input_ptr, input_size)
            output_dataset = create_dataset(output_ptr, output_size)
            started = time.perf_counter()
            check_ret(acl.mdl.execute(model_id, input_dataset, output_dataset), "acl.mdl.execute")
            latency_ms = (time.perf_counter() - started) * 1000.0

            output = np.empty(output_size // np.dtype(np.float32).itemsize, dtype=np.float32)
            check_ret(
                acl.rt.memcpy(
                    acl.util.numpy_to_ptr(output),
                    output_size,
                    output_ptr,
                    output_size,
                    ACL_MEMCPY_DEVICE_TO_HOST,
                ),
                "acl.rt.memcpy output",
            )
            return output.reshape(output_shape), latency_ms
        finally:
            destroy_dataset(input_dataset)
            destroy_dataset(output_dataset)
            if input_ptr is not None:
                acl.rt.free(input_ptr)
            if output_ptr is not None:
                acl.rt.free(output_ptr)


def create_dataset(ptr: int, size: int) -> Any:
    dataset = acl.mdl.create_dataset()
    buffer = acl.create_data_buffer(ptr, size)
    check_ret(acl.mdl.add_dataset_buffer(dataset, buffer), "acl.mdl.add_dataset_buffer")
    return dataset


def destroy_dataset(dataset: Any | None) -> None:
    if dataset is None:
        return
    buffer_count = int(checked_value(acl.mdl.get_dataset_num_buffers(dataset), "acl.mdl.get_dataset_num_buffers"))
    for index in range(buffer_count):
        buffer = acl.mdl.get_dataset_buffer(dataset, index)
        acl.destroy_data_buffer(buffer)
    acl.mdl.destroy_dataset(dataset)


def check_ret(ret: Any, operation: str) -> None:
    code = ret[-1] if isinstance(ret, tuple) else ret
    if code != 0:
        raise RuntimeError(f"{operation} failed with ret={code}")


def checked_value(result: Any, operation: str) -> Any:
    if not isinstance(result, tuple):
        return result
    *values, ret = result
    check_ret(ret, operation)
    if len(values) == 1:
        return values[0]
    return tuple(values)


if __name__ == "__main__":
    main()
