# Voice Provider Boundary

本文档固定 `astrbot_plugin_proactive_chat` v0.2 的语音边界。它是实现前的验收设计，不代表当前 `0.1.6` 已经完成所有状态探测。

## 目标

主插件继续复用 AstrBot 当前 STT/TTS provider 作为默认 bridge，同时为后续独立 voice provider 插件留下稳定接口。

这个边界解决三个问题：

- 主插件不绑定任何单一语音 provider。
- provider 状态可以通过 `/proactive_status` 公开安全地诊断。
- 社区可以复制模板仓库实现自己的 STT/TTS provider。

## 所有权边界

主插件负责：

- 读取 `voice_input_enabled` 和 `voice_output_enabled`。
- 从 QQ 群聊事件提取语音消息并入队。
- 消费 `voice_group_message`。
- 在 STT 成功后调用 LLM。
- 在 TTS 成功后发送 `Record` 音频段。
- 在 TTS 或音频发送失败时回退文本。
- 记录 queue job state、delivery state 和 public-safe failure code。

voice provider 负责：

- STT/TTS provider credentials。
- endpoint、模型名、voice name、timeout 等 provider 配置。
- provider 专属请求和响应格式。
- provider rate limit 和错误映射。
- provider 自己的测试和文档。

voice provider 不负责：

- queue schema。
- proactive policy。
- persona 或 memory。
- group allowlist。
- quiet hours、cooldown、daily cap。
- AstrBot message delivery。

## 最小协议

主插件只依赖以下抽象能力：

```python
from typing import Literal


class SpeechToTextProvider:
    async def transcribe(self, unified_msg_origin: str, audio_url: str) -> str: ...


class TextToSpeechProvider:
    async def synthesize(self, unified_msg_origin: str, text: str) -> str: ...


VoiceProviderStatus = Literal["available", "missing", "failed", "disabled"]
```

参数约束：

- `unified_msg_origin` 用于让 provider 选择 AstrBot 会话级配置。
- `audio_url` 是音频引用，不能是 inline base64 payload。
- `text` 是已经由 LLM 生成、准备回复给群聊的文本。

返回值约束：

- `transcribe()` 返回去除首尾空白后可用于 LLM 的文本。
- `synthesize()` 返回可交给 AstrBot `Record` 消息段的音频引用。
- 空 STT 文本按 `empty_stt_response` 处理，不调用 LLM。

## Provider 状态

v0.2 引入公开状态，不暴露 provider 内部对象：

```text
available
missing
failed
disabled
```

状态含义：

- `available`：配置启用，provider 存在，最小探测通过或可被安全认为可用。
- `missing`：配置启用，但 AstrBot 当前没有可用 provider。
- `failed`：配置启用，provider 存在，但最小探测失败。
- `disabled`：对应语音输入或输出未启用，主插件不检查 provider。

推荐的 public failure code：

```text
stt_provider_unavailable
tts_provider_unavailable
stt_probe_failed
tts_probe_failed
empty_stt_response
invalid_voice_payload
voice_delivery_failed
```

## `/proactive_status` 输出

v0.2 在现有状态输出后追加 voice 区块：

```text
voice:
- input: enabled
- output: disabled
- stt_provider: available
- tts_provider: disabled
```

如果失败，只显示 public failure code：

```text
voice:
- input: enabled
- output: enabled
- stt_provider: failed stt_probe_failed
- tts_provider: missing tts_provider_unavailable
```

禁止输出：

- provider token
- Authorization header
- cookie
- 完整签名 URL
- 本地敏感路径
- inline base64
- 原始音频 payload
- provider 原始异常堆栈

## Worker 行为

语音输入：

- `voice_input_enabled=false` 时，语音消息不入队。
- `voice_input_enabled=true` 且群号 allowlisted 时，纯语音消息入队为 `voice_group_message`。
- 文本和语音混合消息固定文本优先，避免重复入队。
- STT provider missing/failed 时，job failed，不调用 LLM。
- STT 返回空文本时，job failed，不调用 LLM。

语音输出：

- `voice_output_enabled=false` 时，只发送文本。
- `voice_output_enabled=true` 且 TTS 成功时，发送 `Record` 音频。
- TTS missing/failed 或音频发送失败时，回退文本。
- 只有语音或文本最终成功投递后，才记录 rate limit。
- 语音和文本投递都失败时，不记录 rate limit。

## Provider 模板仓库

模板仓库名：

```text
astrbot_plugin_proactive_voice_template
```

模板必须包含：

- `metadata.yaml`
- `_conf_schema.json`
- provider adapter 示例
- fake STT/TTS provider
- README 中文安装说明
- pytest 覆盖 available、missing、failed 和 redaction

模板不得包含：

- 大型模型或二进制权重
- 真实 API key
- provider token 示例值
- proactive queue 实现
- persona、memory 或 policy 逻辑

## 本地 HTTP Provider

第一个真实 provider 插件方向固定为本地 HTTP：

```text
astrbot_plugin_proactive_voice_http
```

STT 请求：

```text
POST /v1/stt
```

最小响应：

```json
{"text": "今天聊什么？"}
```

TTS 请求：

```text
POST /v1/tts
```

最小响应二选一：

```json
{"audio_url": "http://127.0.0.1:9000/audio/abc.wav"}
```

```json
{"audio_path": "/path/to/generated.wav"}
```

本地 HTTP provider 插件负责：

- endpoint
- timeout
- voice name
- 可选认证 token
- HTTP 错误到 public failure code 的映射

主插件不得直接依赖 HTTP endpoint、HTTP client、provider token 或 provider-specific response shape。

## 测试门禁

后续实现必须覆盖：

- `tests/test_voice.py`
  - STT/TTS provider available。
  - missing provider 映射为 public failure code。
  - probe failure redaction。

- `tests/test_management.py`
  - `/proactive_status` 包含 voice input/output 状态。
  - `/proactive_status` 包含 STT/TTS provider 状态。
  - status 不泄露 token、Authorization、cookie、完整 URL、base64、本地路径。

- `tests/test_worker.py`
  - 现有语音输入测试继续通过。
  - STT 失败不调用 LLM。
  - TTS 失败回退文本。
  - 语音和文本投递都失败时不计入 rate limit。

发布前仍必须跑：

```bash
uv run python scripts/smoke_check.py
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv build
```
