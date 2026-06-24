# 接入 DeepSeek 维修建议 API

## Goal

让故障中心的维修建议生成可以直接使用 DeepSeek 官方 API。后端在配置
`EDGEEYE_LLM_PROVIDER=deepseek` 和本地 API key 后，应调用 DeepSeek chat
completions，要求返回中文 JSON，并把生成结果保存到现有 `advice` 表。

用户价值：维修建议不再只能依赖通用规则模板；配置 DeepSeek 后，页面展示的
风险分析、检查步骤、维修建议和安全注意事项来自大模型生成并可持久化复用。

## Confirmed Facts

- 当前后端已有维修建议持久化流程：`POST /api/advice/generate` 会先查
  `advice` 表，没有记录时生成并写入数据库。
- 当前后端已有 OpenAI-compatible 调用路径和 JSON 解析逻辑，配置项使用
  `EDGEEYE_LLM_*` 环境变量。
- 当前前端只展示后端返回的 `Advice` 字段，不负责生成维修建议内容。
- DeepSeek 官方文档提供 OpenAI API format 的
  `https://api.deepseek.com/chat/completions` 入口。
- DeepSeek JSON Output 文档要求设置 `response_format: {"type": "json_object"}`，
  并在提示词中明确要求 json 输出。
- 用户提供的 key 属于敏感信息，只能用于本地环境变量，不得写入代码、文档、
  `.env.example` 或提交内容。

## Requirements

- 支持 `EDGEEYE_LLM_PROVIDER=deepseek`。
- 当 provider 为 `deepseek` 且未显式设置 URL 时，默认调用 DeepSeek 官方
  chat-completions endpoint。
- 当 provider 为 `deepseek` 且未显式设置模型时，使用适合维修建议 JSON 生成的
  DeepSeek 默认模型。
- 请求体必须继续要求中文 JSON，字段包含：
  `possibleCauses`、`riskAnalysis`、`inspectionSteps`、
  `maintenanceSuggestions`、`safetyNotes`。
- 成功调用 DeepSeek 后，建议内容必须写入数据库，`adviceStatus=ready`，
  `modelName` 记录实际模型名。
- DeepSeek 调用失败、超时、返回空内容或非法 JSON 时，继续保存规则模板降级建议，
  不向前端暴露 provider 内部错误。
- 配置示例和 README 必须说明 DeepSeek 本地配置方式，但不能包含真实 key。
- 需要有自动化测试覆盖 DeepSeek provider 的 URL、模型名、鉴权头、JSON mode 和
  持久化结果。

## Acceptance Criteria

- [x] `EDGEEYE_LLM_PROVIDER=deepseek` 可在不设置 `EDGEEYE_LLM_API_URL` 时解析到
      DeepSeek 官方 endpoint。
- [x] DeepSeek provider 请求携带 `Authorization: Bearer <key>`，请求体包含
      `response_format: {"type": "json_object"}` 和中文 json 输出提示。
- [x] DeepSeek provider 成功返回后，`GET /api/faults/{faultId}/advice` 能读取到
      已保存的中文建议。
- [x] 失败时仍返回并保存中文规则模板建议，且不泄露异常类型或密钥。
- [x] `backend/.env.example`、`README.md`、`backend/README.md` 记录 DeepSeek 配置方式。
- [x] `cd backend && uv run pytest` 通过。
- [x] 若可用 key 已在本地环境中配置，完成一次真实 DeepSeek 调用 smoke；若 key 不可用，
      明确报告未运行原因。

## Notes

- 不新增前端页面行为；本任务只完善后端 LLM provider、配置文档和验证。
