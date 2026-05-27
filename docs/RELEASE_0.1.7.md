# v0.1.7 Release Notes

`v0.1.7` 是 `astrbot-plugin-proactive-chat` 的语音诊断 patch 版本。

## 推荐安装

```bash
uv pip install astrbot-plugin-proactive-chat==0.1.7
```

依赖会自动安装：

```text
astrbot-proactive-core>=0.1.0,<0.2.0
```

## 主要变化

- `/proactive_status` 新增 `voice:` 区块。
- 显示语音输入和语音输出是否启用。
- 显示 STT/TTS provider 状态：
  - `available`
  - `missing`
  - `failed`
  - `disabled`
- provider 失败时只显示 public failure code，例如 `stt_provider_unavailable`、`tts_provider_unavailable`、`stt_probe_failed`、`tts_probe_failed`。
- status 输出会脱敏 token、Authorization header、cookie、完整 URL、base64 payload 和本地路径。

## 兼容性

- 没有 STT/TTS provider 时，文本链路仍然可用。
- 语音输入和语音输出默认仍关闭。
- 现有 worker 语义保持不变：STT 失败不调用 LLM，TTS 失败回退文本，语音和文本投递都失败时不计入限流。
- 不引入新的 provider 依赖，不内置 OpenAI、Gemini 或本地模型。

## 验证

发布前门禁：

```bash
uv run python scripts/smoke_check.py
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv build
```

本地验证结果：

- `smoke_check.py`：通过
- pytest：`84 passed`
- ruff：通过
- build：通过

## 已知限制

- 本版本只把 voice provider status 做进主插件。
- 独立 provider 模板仓库尚未创建。
- 本地 HTTP voice provider 插件尚未实现。
- 如通过 PyPI 安装，请确认安装的是 `0.1.7` 而不是旧版 `0.1.6`。
