# 成员1：Atlas 开发板与边缘推理

## Goal

在 Atlas 开发板上打通 EdgeEye 的边缘端最小联调链路：摄像头采集、模型推理、结果后处理、关键帧筛选、本地留存和按 `POST /api/detection/results` 上传后端。最终目标是让前端能够看到来自真实或可替代视频源的实时检测结果、标注图和性能数据。

本任务先完成 Trellis 规划和协作边界，不立即进入业务代码实现。实现开始前必须由用户确认开发板环境与联调输入。

## Confirmed Facts

- 项目已初始化 Trellis，本任务创建于 `.trellis/tasks/06-17-edge-atlas`，负责人和创建者均为 `EIR`。
- 成员1职责来自 `docs/01-edge-atlas.md`：Atlas 环境、摄像头接入、模型转换部署、OM/ACL 推理、结果绘制上传、性能与稳定性测试。
- 成员1必须使用成员2提供的目标检测模型、`classes.json`、`label.names` 和预处理参数。
- 成员1对接成员4后端，主上传接口是 `POST /api/detection/results`。
- 上传数据契约以 `docs/contracts.md`、`docs/openapi.yaml`、`docs/api-spec.md` 为准。
- 当前最小联调方案要求图片先保存成后端可访问 URL，再用 JSON 上传；不能在同一个 `/api/detection/results` 路径下混用 multipart。
- Atlas 上传 `Detection`，后端负责生成 `Fault`、`Alarm`、`Advice` 和报告；Atlas 上传体不得包含 `faults`。
- 坐标必须是原始图片像素坐标 `[x1, y1, x2, y2]`，并满足图片边界约束。
- 关键帧策略要求正常状态限速上传、新故障立即上传、故障持续按间隔上传、故障恢复上传恢复帧。
- 当前运行环境主机名为 `davinci-mini`，架构为 `aarch64`，内核为 `Linux 5.10.0+`，系统为 `Ubuntu 22.04 LTS`。
- 当前开发板设备树标识为 `Hisilicon PhosphorHi1910B evb`。
- 当前 Python 版本为 `3.9.2`，OpenCV 可导入且版本为 `4.7.0`。
- Ascend toolkit 路径存在：`/usr/local/Ascend/ascend-toolkit/7.0.RC1`；版本文件显示 `Version=7.0.0.5.242`、`version_dir=7.0.RC1`，`atc` 位于 `/usr/local/Ascend/ascend-toolkit/7.0.RC1/aarch64-linux/bin/atc`，`/usr/local/Ascend/ascend-toolkit/latest/bin/atc` 也是可用入口。
- `acl` Python 模块可导入；宿主环境中 `acl.init()` 返回 `0`，`acl.rt.get_device_count()` 返回 `(1, 0)`，`acl.rt.set_device(0)` 和 `acl.rt.reset_device(0)` 也成功。
- 宿主环境已存在 `/dev/davinci_manager`、`/dev/davinci0`、`/dev/upgrade`、`/dev/davinci_manager_docker`、`/dev/hi_mipi_rx`；`ACL_DEVICE_ID` 可直接记录为 `0`。
- `npu-smi info -t product -i 0` 显示商业型号为 `Atlas 200I A2`，`Product Name=IT22MMDB`，`Manufacturer=Huawei`，`Firmware Version=7.0.0.5.242`，`Board ID=0x45`，`PCB ID=B`，`BOM ID=1`。
- `soc_version` 可先按 `Ascend310B4` 记录；`npu-smi` 输出和 Ascend toolkit 平台配置都包含 `310B4`。
- USB 摄像头已接入并被识别为 `Alcor Micro, Corp. PC Camera`，USB ID 为 `058f:1412`，连接链路是 `usb-xhci-hcd.1.auto-1.1`，`uvcvideo` 识别为 UVC 1.00 设备。
- sysfs 已出现摄像头视频设备：`/sys/class/video4linux/video0` 和 `/sys/class/video4linux/video1`，major/minor 分别为 `81:0` 和 `81:1`，名称均为 `PC Camera: PC Camera`。
- `/dev/video0`、`/dev/video1` 和 `/dev/media0` 已可用；`v4l2-ctl --list-devices` 能列出 `PC Camera: PC Camera`。
- `/dev/video0` 是 Video Capture 节点，`/dev/video1` 是 Metadata Capture 节点；`/dev/video0` 支持 MJPG 和 YUYV，已确认的测试配置是 MJPG `640x480 @ 30 FPS`，并支持 `800x600`、`1280x720`、`1280x960` 等分辨率。
- 已保存测试截图和视频到任务目录：`camera-usb-video0-640x480.jpg`、`camera-usb-video0-640x480-warmup.jpg`、`camera-usb-video0-640x480-3s.mjpeg`。
- OpenCV 读取 `/dev/video0` 成功，返回 `opened=True`、`ok=True`，图像尺寸为 `(480, 640, 3)`；但当前截图内容几乎全黑，说明链路可读帧，但画面需要重新对准或补光后再做演示级复测。
- 2026-06-18 仓库更新后重新验证 USB 摄像头：`v4l2-ctl --list-devices` 仍能识别 `PC Camera: PC Camera`，`/dev/video0` 仍是 Video Capture 节点，当前格式为 MJPG `640x480 @ 30 FPS`。
- 2026-06-18 使用 `v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=1 --stream-to=/tmp/edgeeye-video0-frame.mjpg` 直接抓帧成功，已保存证据图片 `camera-usb-video0-2026-06-18-v4l2.jpg`；该帧是 `640x480` JPEG，OpenCV `imread` 可解码为 `(480, 640, 3)`，平均亮度约 `1.83`，画面仍接近全黑。
- 2026-06-18 当前系统 Python/OpenCV 通过 `cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)` 打开设备失败，返回 `opened_before_read=False`；这与 V4L2 直接抓帧成功不同，后续边缘端代码应优先把“V4L2 可读、OpenCV 需兼容处理”作为摄像头输入层风险处理。
- 仓库当前没有 `edge-app/` 边缘端业务实现目录；本阶段不修改模型资产、模型 runner 或推理逻辑，只确认摄像头链路和前后端接口入口。
- 后端已提供边缘端上传接口：`POST /api/detection/results`，路由位于 `backend/app/api/routes/inspections.py`，请求模型为 `DetectionUploadRequest`，响应模型为 `DetectionUploadResult`。
- `DetectionUploadRequest` 当前要求 JSON 上传，必须包含 `idempotencyKey`、`inspectionId`、`frameId`、`timestamp`、`isKeyFrame`、`uploadReason`、`imageUrl`、`imageWidth`、`imageHeight`、`detections` 和 `performance`；`annotatedImageUrl`、`frameSeq`、`deviceId`、`eventKey`、`sampleWindow` 可按场景提供。
- 后端会校验检测框必须满足 `0 <= x1 < x2 <= imageWidth` 和 `0 <= y1 < y2 <= imageHeight`；`Performance.npuUsage` 允许为 `null`，便于开发板指标不可用时降级上传。
- 后端会按 `idempotencyKey` 做幂等：相同内容重复上传返回 `duplicate=true`，同键不同内容返回 `IDEMPOTENCY_CONFLICT`。
- 前端实时页当前不直接连摄像头，而是通过 `web/src/api/client.ts` 先取 `/api/inspections?pageSize=1` 的最新巡检，再请求 `GET /api/inspections/{inspectionId}/latest-result`；`web/src/pages/RealtimePage.tsx` 使用 `annotatedImageUrl ?? imageUrl` 展示画面并按原图尺寸绘制检测框。
- 2026-06-18 后端接口测试已通过：在 `backend/` 下执行 `env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest`，结果 `11 passed, 1 warning`，覆盖检测上传、latest-result、幂等冲突、bbox 越界和缺失 NPU 指标。
- 仓库当前未发现 `edge-app/`、`camera/`、`model-deploy/`、`config/`、`logs/` 目录，也未发现 `.om`、`.onnx`、`.pt`、`classes.json`、`label.names` 或演示视频/图片资产；在系统常见目录中也未找到可直接使用的项目级 `.om` 模型文件。
- 2026-06-18 已将无模型摄像头桥并入后端进程：后端启动时默认尝试用 ffmpeg 从 `/dev/video0` 抓取 `640x480` JPEG，保存到 `uploads/raw/{inspectionId}/{frameId}.jpg`，并通过后端服务层写入空 `detections` 的 `periodic_sample` 结果；不再需要单独启动 edge 脚本。
- 当前后端不包含视觉检测模型，也不是模型推理服务；它提供 inspection lifecycle、detection upload、latest-result、fault/alarm/advice/report 等 API。视觉模型仍应在边缘端接入，后续只填充现有上传 payload 的 `detections` 字段，不应改接口参数。
- 2026-06-18 后端内置桥保留与独立脚本相同的存储和 latest-result 契约；前端仍通过现有 `/api/inspections/{inspectionId}/latest-result` 展示最新帧。
- 2026-06-18 前端已按现有 API 增加实时快照轮询：登录后每 1 秒刷新一次 `/api/inspections/{inspectionId}/latest-result` 链路，不新增接口参数或启动步骤。
- 2026-06-19 为解决 1 FPS 抓拍轮询卡顿和 raw 文件持续增长，实时显示改为后端内置 `GET /api/camera/stream.mjpg` MJPEG 长连接；latest-result 继续负责检测框、性能、故障和报告证据数据。
- 2026-06-19 后端摄像头桥默认使用单个 ffmpeg MJPEG 长进程作为摄像头拥有者；实时流不落盘，后台仅按 `EDGEEYE_CAMERA_INTERVAL_SECONDS` 保存低频 raw 样本，并按 `EDGEEYE_CAMERA_MAX_RAW_FRAMES_PER_INSPECTION` 清理旧样本。

## Requirements

### Functional Requirements

- 提供边缘端运行目录和配置方案，覆盖后端地址、摄像头源、模型路径、类别文件、阈值、上传间隔、本地队列大小和图片输出目录。
- 支持摄像头或视频文件作为输入源；真实摄像头不可用时，允许先用视频文件完成最小联调。
- 当前小阶段只做摄像头硬件烟测和前后端接口确认，不改动模型资产、模型推理接口或后处理逻辑。
- 在模型资产未交付前，由后端进程内置无模型摄像头实时桥：上传空 `detections`，让前端可以先看到真实 USB 摄像头画面，且用户只需要启动后端和前端。
- 实时画面必须优先走后端 MJPEG 流，不再依赖每秒保存 JPEG 后让前端轮询图片。
- 无模型阶段不得连续写 MP4 或保存每个视频帧；只保留 latest-result/证据所需的低频样本，并设置保留上限。
- 支持单帧采集和连续读取，并记录摄像头断开、读帧失败和重连状态。
- 支持加载成员2交付的 ONNX/OM 模型资产，保留 `best.pt -> ONNX -> ATC -> OM -> ACL` 的转换记录。
- 板端推理预处理必须与工程规范一致：BGR 转 RGB、resize 到模型输入尺寸、归一化到 `[0, 1]`、HWC 转 CHW、增加 batch 维度、输入 `NCHW`。
- 后处理必须包含置信度过滤、坐标映射回原图、NMS、类别映射和 `Detection` 结构生成。
- 检测结果必须包含 `category`、`deviceType` 或 `faultType`、`confidence`、`bbox`。
- 绘制并保存原图和标注图，路径遵守 `raw/{inspectionId}/{frameId}.jpg` 和 `annotated/{inspectionId}/{frameId}.jpg` 约定。
- 上传 payload 必须包含 `idempotencyKey`、`inspectionId`、`frameId`、`timestamp`、`isKeyFrame`、`uploadReason`、`imageUrl`、`imageWidth`、`imageHeight`、`detections`、`performance`。
- 默认 `idempotencyKey` 使用 `{inspectionId}:{frameId}`。
- 上传失败时必须保留本地 outbox，后端 ACK 后再标记成功；至少保留最近一批待上传结果，避免联调数据丢失。
- 统计并上传推理延迟、FPS、CPU、内存和 NPU 使用率；NPU 指标在开发板命令不可用时允许返回 `null` 或降级记录，但必须写明原因。
- 提供本地健康检查能力，至少能报告模型路径、类别文件、ACL/CANN 初始化状态、摄像头状态和最近一帧时间。

### Collaboration Requirements

- 用户负责在开发板上执行硬件和环境命令，并把输出贴回；本任务根据输出调整配置、命令和代码。
- 用户负责提供或确认成员2模型资产位置：ONNX/OM、`classes.json`、`label.names`、输入尺寸和阈值。
- 用户负责提供或确认后端联调地址；如果后端未部署，先以本机或演示后端地址配置。
- 我负责维护 Trellis 任务、规划文档、边缘端代码结构、配置模板、上传契约适配和验证清单。
- 作为成员 `EIR`，我需要在完成一次有意义的文件更新后及时创建对应 git commit，避免多个阶段的改动混在一起。
- 作为成员 `EIR`，我需要在完成一次大更新后将本地提交 push 到远程分支，确保协作方可以拉取最新规划和实现。
- commit 和 push 前必须检查 `git status`，只提交本任务相关文件，不混入其他成员或无关改动。
- push 前必须至少完成当前阶段合理的验证；如果验证无法运行，需要在提交说明或最终汇报中写明原因。
- 除 Trellis 任务、Agent skills、协作文档等元数据更新外，后续业务代码实现类改动应优先在新分支完成，避免多人直接在 `main` 上并行提交互相影响。
- 推荐业务实现分支名为 `eir/edge-atlas`，或按具体里程碑扩展为 `eir/edge-atlas-<topic>`。

### Constraints

- 不新增未登记的接口字段、枚举或 API 路径；如确需变更，先同步更新 `docs/contracts.md` 和 `docs/openapi.yaml`。
- 边缘端不得直接生成或上传 `Fault`、`Alarm`、`Advice`。
- 正常状态不得每帧上传；必须通过关键帧策略限制上传频率。
- 业务实现开始前，Trellis 任务必须仍处于 `planning`，并且用户确认规划可以进入执行。
- 不在未检查工作区状态的情况下提交；不提交其他成员未确认的改动；不在未确认远程分支策略时强制推送。
- 不在 `main` 上直接展开较大的业务代码改动，除非用户明确要求或只是 Trellis/文档类小更新。

## Acceptance Criteria

- [ ] Trellis 任务由 `EIR` 认领，规划文档包含成员1目标、边界、协作方式和验收条件。
- [ ] `EIR` 的 git 协作职责被记录：小步更新后 commit，大更新后 push，提交前检查工作区并避免混入无关文件。
- [ ] `EIR` 的分支策略被记录：业务代码优先在新分支更新，Trellis/Agent skills/文档类小更新可按当前协作流程处理。
- [x] 开发板基础环境信息被记录：板端标识、系统版本、CANN toolkit 版本、Python 版本、OpenCV 状态。
- [ ] 开发板设备节点状态被进一步确认：NPU 设备节点已可用，模型资产位置仍待确认。
- [x] 可从摄像头或视频源读取画面，至少能保存一张原始测试图片。
- [x] 当前 USB 摄像头可通过 V4L2 直接抓取 `640x480` JPEG 测试帧，证据图片已保存到任务目录。
- [x] 已确认后端存在边缘端上传入口 `POST /api/detection/results`，前端实时页通过 latest-result 间接展示边缘端结果。
- [x] 已验证后端接口测试通过，检测上传、幂等、latest-result、bbox 校验和 `npuUsage: null` 行为可用。
- [x] 本阶段未修改模型资产、模型 runner、推理后处理或模型接口。
- [x] 已新增后端内置无模型实时摄像头桥，按现有数据契约写入空检测结果，前端可通过 latest-result 展示真实摄像头帧。
- [x] 前端实时巡检页会自动刷新 latest-result 快照，用户只需启动后端和前端即可观察摄像头画面变化。
- [x] OpenCV 当前无法直接打开 `/dev/video0` 的问题已通过 ffmpeg/V4L2 可替换 capture backend 绕开；默认配置使用 ffmpeg。
- [x] 已新增后端 MJPEG 实时流 `GET /api/camera/stream.mjpg`，前端实时页优先使用该流显示画面。
- [x] 实时显示不按视频帧落盘；无模型 raw 样本改为低频保存并限制每次巡检保留数量。
- [ ] Atlas 能运行至少一个目标检测模型；若真实 OM/ACL 暂不可用，必须提供可替代的本地 mock/ONNX 调试路径并明确切换条件。
- [ ] 推理结果能转换为 EdgeEye `Detection` 结构，bbox 坐标基于原图尺寸且通过边界校验。
- [ ] 能保存原图和标注图，并生成后端可访问的 `imageUrl` 与 `annotatedImageUrl`。
- [ ] 能按 `POST /api/detection/results` 契约上传关键帧 JSON，后端返回 accepted 或 duplicate 时视为成功。
- [ ] 后端不可用时上传任务进入本地 outbox，不导致推理主循环崩溃。
- [ ] 能显示或记录 latency、FPS、CPU、内存和 NPU 使用率。
- [ ] 摄像头断开、模型加载失败、ACL 错误和上传失败都有明确日志。
- [ ] 连续运行不少于 30 分钟的稳定性测试有记录。
- [ ] 前端可以通过后端看到来自边缘端的最新检测结果。

## Out of Scope

- 训练目标检测模型。
- 设计新的故障规则、风险等级映射或大模型维修建议内容。
- 实现后端数据库、告警、报告或前端页面。
- 仪表读数识别、多摄像头、温湿度传感器和复杂权限系统。
- 在未同步契约文档的情况下新增 API 字段或枚举。

## Open Questions

- 模型资产位置尚未由用户确认，且系统常见目录里未发现可直接使用的项目级 `.om` 模型文件。
- 后端联调地址是否已可从开发板访问尚未确认。
- 成员2是否已经交付可转换或可直接运行的 ONNX/OM 模型尚未确认。
- 边缘端摄像头读取实现应优先修复 OpenCV `VideoCapture` 打开失败，还是直接采用已验证可用的 V4L2/ffmpeg/GStreamer 路径，尚待执行阶段决定。
- 模型资产仍未确认，下一阶段只能继续完善 capture/upload/outbox 或接入 mock 检测；不能实现真实 YOLO/ACL 检测。

## Notes

- 本任务是复杂任务，需配套 `design.md` 和 `implement.md` 后再进入执行。
