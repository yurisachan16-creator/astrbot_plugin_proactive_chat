# v0.2 模块拆分路线

v0.2 的核心方向是 voice provider boundary，而不是继续把所有能力塞进 proactive chat 主插件。

## 架构原则

`astrbot_plugin_proactive_chat` 只负责：

- AstrBot 插件入口。
- 群聊事件提取。
- 主动消息策略。
- 队列消费。
- 限流和免打扰。
- 调用已选择的 LLM/STT/TTS provider。
- 文本或语音投递。

provider 插件负责：

- provider 凭据。
- provider 专属请求格式。
- provider 限流和错误映射。
- provider 专属测试。
- provider 文档。

## v0.2 不做

- 不做长期 memory。
- 不做 WebUI。
- 不做 Telegram。
- 不做视觉/game adapter。
- 不重写 `astrbot_proactive_core` 为 daemon。

## 拆分步骤

### 1. 固定 voice adapter 协议

在当前 `proactive_chat.voice` 基础上，明确最小协议：

```python
class SpeechToTextProvider:
    async def transcribe(self, audio: object) -> str: ...

class TextToSpeechProvider:
    async def synthesize(self, text: str) -> object: ...
```

实际实现可以继续包一层 AstrBot 当前 provider，不直接暴露 provider 内部对象。

### 2. 增加 provider capability 检查

启动时给 `/proactive_status` 增加 voice provider 状态：

- STT provider：可用 / 未配置 / 调用失败
- TTS provider：可用 / 未配置 / 调用失败

失败信息必须走 public-safe failure code，不暴露 token 或完整 URL。

### 3. 建 provider 插件模板仓库

建议仓库名：

```text
astrbot_plugin_proactive_voice_template
```

模板只包含：

- provider manifest
- 最小配置 schema
- STT/TTS adapter 示例
- 本地 fake provider 测试
- README 中文安装说明

### 4. 做第一个真实 provider 插件

候选优先级：

1. 本地 HTTP TTS/STT provider：最适合个人部署，依赖最少。
2. OpenAI TTS/STT provider：接口稳定，文档清楚，但需要外部 API key。
3. Gemini provider：等 v0.2 边界稳定后再做。

推荐从本地 HTTP provider 开始，因为它更贴合 Neuro-sama/AIRI-like 的长期开源部署方向。

## 数据流

```mermaid
flowchart LR
    A["群聊消息"] --> B["proactive_chat 事件提取"]
    B --> C["astrbot_proactive_core SQLiteQueue"]
    C --> D["AmbientWorker"]
    D --> E["AstrBot LLM provider"]
    D --> F["Voice adapter protocol"]
    F --> G["AstrBot 当前 STT/TTS provider"]
    F -.v0.2.-> H["独立 voice provider 插件"]
    D --> I["AstrBotMessenger 投递"]
```

## v0.2 验收标准

- 主插件不依赖任何单一语音 provider。
- 没有 provider 时，文本链路仍然可用。
- STT/TTS 失败时，任务状态和投递状态可诊断。
- provider 错误不泄露密钥。
- 至少一个 provider 插件模板可以被社区复制使用。
