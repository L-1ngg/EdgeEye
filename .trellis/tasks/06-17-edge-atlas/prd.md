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
- Ascend toolkit 路径存在：`/usr/local/Ascend/ascend-toolkit/7.0.RC1`，toolkit/ATC 版本文件显示 `Version=7.0.0.5.242`、`version_dir=7.0.RC1`。
- `acl` Python 模块可导入，但导入时报告无法打开 `/dev/davinci_manager`。
- 当前未发现 `/dev/davinci*`、`/dev/davinci_manager` 或 `/dev/video*` 设备节点；`npu-smi info` 失败，错误指向 NPU 驱动设备节点不可用。
- 仓库当前未发现 `edge-app/`、`camera/`、`model-deploy/`、`config/`、`logs/` 目录，也未发现 `.om`、`.onnx`、`.pt`、`classes.json`、`label.names` 或演示视频/图片资产。

## Requirements

### Functional Requirements

- 提供边缘端运行目录和配置方案，覆盖后端地址、摄像头源、模型路径、类别文件、阈值、上传间隔、本地队列大小和图片输出目录。
- 支持摄像头或视频文件作为输入源；真实摄像头不可用时，允许先用视频文件完成最小联调。
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

### Constraints

- 不新增未登记的接口字段、枚举或 API 路径；如确需变更，先同步更新 `docs/contracts.md` 和 `docs/openapi.yaml`。
- 边缘端不得直接生成或上传 `Fault`、`Alarm`、`Advice`。
- 正常状态不得每帧上传；必须通过关键帧策略限制上传频率。
- 业务实现开始前，Trellis 任务必须仍处于 `planning`，并且用户确认规划可以进入执行。
- 不在未检查工作区状态的情况下提交；不提交其他成员未确认的改动；不在未确认远程分支策略时强制推送。

## Acceptance Criteria

- [ ] Trellis 任务由 `EIR` 认领，规划文档包含成员1目标、边界、协作方式和验收条件。
- [ ] `EIR` 的 git 协作职责被记录：小步更新后 commit，大更新后 push，提交前检查工作区并避免混入无关文件。
- [x] 开发板基础环境信息被记录：板端标识、系统版本、CANN toolkit 版本、Python 版本、OpenCV 状态。
- [ ] 开发板设备节点状态被解决或明确降级：NPU 设备节点、摄像头设备节点、模型资产位置。
- [ ] 可从摄像头或视频源读取画面，至少能保存一张原始测试图片。
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

- Atlas 开发板的商业型号仍需用户确认；目前只能从设备树看到 `Hisilicon PhosphorHi1910B evb`。
- 当前 NPU 设备节点和摄像头设备节点不可见，需要确认驱动服务、权限、设备连接或容器/沙箱透传状态。
- 摄像头类型和模型资产位置尚未由用户确认。
- 后端联调地址是否已可从开发板访问尚未确认。
- 成员2是否已经交付可转换或可直接运行的 ONNX/OM 模型尚未确认。

## Notes

- 本任务是复杂任务，需配套 `design.md` 和 `implement.md` 后再进入执行。
