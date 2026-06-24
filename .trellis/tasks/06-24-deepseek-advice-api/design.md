# 接入 DeepSeek 维修建议 API 设计

## Architecture

现有维修建议链路保持不变：

```text
Frontend -> POST /api/advice/generate -> InspectionService.generate_advice()
  -> _generate_advice_payload()
    -> DeepSeek provider or rule-template fallback
  -> INSERT INTO advice
Frontend -> GET /api/faults/{faultId}/advice -> saved advice
```

本任务只扩展后端 provider 解析和配置，不改变 API 路由、响应字段、数据库表结构或前端展示契约。

## Provider Resolution

`EDGEEYE_LLM_PROVIDER` 支持：

- `rule-template`: 强制使用本地规则模板。
- `openai-compatible`: 使用显式配置的 `EDGEEYE_LLM_API_URL` 和 `EDGEEYE_LLM_MODEL_NAME`。
- `deepseek`: 使用 DeepSeek 官方 OpenAI-compatible chat-completions API。

DeepSeek 默认值：

- URL: `https://api.deepseek.com/chat/completions`
- model: `deepseek-v4-pro`

如果用户显式配置 `EDGEEYE_LLM_API_URL` 或 `EDGEEYE_LLM_MODEL_NAME`，以用户配置为准，方便切换代理网关或模型。

## Data Flow

1. `generate_advice()` 根据 `faultId` 查询故障。
2. 如果该故障已有 advice，直接返回数据库记录。
3. `_generate_advice_payload()` 解析 provider 配置。
4. DeepSeek provider 调用 `_call_llm_provider()`，请求体包含：
   - `model`
   - `messages`
   - `temperature`
   - `response_format: {"type": "json_object"}`
5. `_parse_advice_content()` 验证返回 JSON 字段形状。
6. 成功时写入 `advice` 表，状态为 `ready`。
7. 失败时写入中文规则模板，状态为 `fallback`。

## Secrets

真实 API key 只允许通过本地 `backend/.env` 或进程环境变量提供，不写入：

- source code
- `.env.example`
- README/docs
- tests
- Trellis artifacts

## Compatibility

- 不新增接口字段。
- 不改 `Advice` Pydantic 模型。
- 不改 SQLite schema。
- 现有 `openai-compatible` 配置继续可用。

## Rollback

将 `EDGEEYE_LLM_PROVIDER` 改回 `rule-template` 即可恢复纯本地规则模板生成；已有数据库 advice 记录不会自动删除。
