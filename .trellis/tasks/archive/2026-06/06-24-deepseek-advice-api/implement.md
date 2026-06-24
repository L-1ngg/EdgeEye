# 接入 DeepSeek 维修建议 API 实施计划

## Checklist

- [ ] 读取 backend spec 和 logging/error guidelines。
- [ ] 增加 DeepSeek provider 默认 URL 和模型解析逻辑。
- [ ] 保持 OpenAI-compatible provider 的显式 URL 要求。
- [ ] 更新测试，覆盖 DeepSeek URL、模型、Authorization 和 JSON mode。
- [ ] 更新配置示例和 README，不写真实 key。
- [ ] 运行 `cd backend && uv run pytest`。
- [ ] 若本地 key 可用，使用临时环境变量做一次真实调用 smoke。

## Validation Commands

```bash
cd backend && uv run pytest
```

可选真实调用 smoke：

```bash
cd backend
EDGEEYE_LLM_PROVIDER=deepseek \
EDGEEYE_LLM_API_KEY=<local-secret> \
EDGEEYE_CAMERA_BRIDGE_ENABLED=false \
uv run python <smoke-script>
```

## Risky Files

- `backend/app/core/config.py`
- `backend/app/services/inspection_service.py`
- `backend/tests/test_member4_api.py`
- `backend/.env.example`
- `README.md`
- `backend/README.md`

## Rollback Points

- Revert provider resolution changes.
- Set `EDGEEYE_LLM_PROVIDER=rule-template` locally if DeepSeek is unavailable.
