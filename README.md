# astrbot_plugin_proactive_chat

面向 AstrBot 的主动消息社区插件骨架，目标是做成类似 AIRI / Neuro-sama 的“在群里有存在感”的 Bot 能力。

当前 v0 只先固定插件形态、配置入口和安全默认值，还不直接开启主动发言。

默认行为：

- 不启用任何群。
- 主动消息关闭。
- 语音输出关闭。
- 免打扰时间开启。
- 保留一键停用开关。

## 安装

当前 v0 拆成两个仓库：

1. `astrbot-proactive-core`：共享队列和安全错误工具。
2. `astrbot-plugin-proactive-chat`：AstrBot 社区插件入口。

推荐安装当前完整可安装版本：

```bash
uv pip install astrbot-plugin-proactive-chat==0.1.3
```

它会自动安装兼容的核心库：

```text
astrbot-proactive-core>=0.1.0,<0.2.0
```

不要优先安装 `0.1.0` 或 `0.1.1`。`0.1.3` 是当前推荐版本，包含 PyPI runtime dependency、完整 AstrBot 插件入口文件，以及 AstrBot 包路径导入修复。

本地开发安装：

```bash
cd /path/to/astrbot_proactive_core
uv sync --extra dev
uv run --extra dev pytest -q
uv run --extra dev ruff check .

cd /path/to/astrbot_plugin_proactive_chat
uv sync --extra dev
uv run python scripts/smoke_check.py
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

更多实机安装步骤见 [docs/INSTALL_ASTRBOT.md](docs/INSTALL_ASTRBOT.md)。社区上架材料见 [docs/COMMUNITY_LISTING.md](docs/COMMUNITY_LISTING.md)。

## 快速冒烟测试

安装后先保持所有开关关闭，确认插件能加载。然后按顺序打开：

1. `enabled_groups`：填入一个测试群。
2. `ambient_enabled=true`：允许群文本消息入队。
3. `background_worker_enabled=true`：允许后台 worker 处理队列。
4. 按需打开 `voice_input_enabled` 和 `voice_output_enabled`。

可用 `/proactive_status` 查看队列和 worker 状态；可用 `/proactive_once` 手动处理一个任务。

本地无 AstrBot 环境时，也可以先跑 `scripts/smoke_check.py`。它只检查文件、导入和安全默认值，不会发送消息。

已落地的基础模块：

- `ProactiveChatConfig`：把 AstrBot 配置归一化成安全默认值。
- `AstrBotVoiceAdapter`：复用 AstrBot 当前启用的 STT/TTS provider。
- `AstrBotMessenger`：通过 `context.send_message(unified_msg_origin, MessageChain)` 做主动文本发送。
- `ProactiveChatPlugin`：保留 AstrBot `Star`/`register` 入口，同时允许本地无 AstrBot 环境测试。
- `IncomingGroupMessage`：从 AstrBot 群聊事件中提取群号、发送者、文本和 `unified_msg_origin`。
- 群聊事件入口：只有群号在 `enabled_groups` 内且 `ambient_enabled=true` 时，才会把消息入队为 `ambient_group_message`，不会直接调用 LLM 或主动发言。
- `AstrBotLLMAdapter`：复用 AstrBot 当前启用的 LLM provider，生成一条简短群聊回复。
- `AmbientWorker`：每次 claim 一个 `ambient_group_message` 任务，生成回复、主动发送，并把任务完成状态和投递状态分开记录。
- 默认持久队列：未显式注入 queue 时，会尝试用 `astrbot_proactive_core.SQLiteQueue` 创建 `data/proactive_chat.sqlite3`；如果核心包尚未安装，插件仍可加载，但 worker 不会启动。
- 后台 worker：默认关闭。设置 `background_worker_enabled=true` 后，插件 `initialize()` 会启动后台循环，按 `worker_interval_seconds` 轮询队列；`terminate()` 会停止并取消后台任务。
- 主动回复限流：按群应用 `cooldown_seconds` 和 `daily_reply_limit`。限流检查发生在调用 LLM 之前；只有成功投递后才计入冷却和每日额度。`daily_reply_limit=0` 表示当天不允许主动回复。
- 语音输出：`voice_output_enabled=true` 时，worker 会用 AstrBot 当前 TTS provider 生成音频，并通过 `Record` 音频段主动发送；TTS 或语音发送失败时自动回退文本。只有语音或文本最终成功投递后才计入限流。
- 语音输入：`voice_input_enabled=true` 时，纯群聊语音消息会入队为 `voice_group_message`，worker 先做限流，再用 AstrBot 当前 STT provider 转写，之后复用现有 LLM 和投递链路。文本+语音混合消息固定文本优先，避免重复入队。STT 失败或空转写不会调用 LLM，也不会计入限流。
- 管理命令：提供 `/proactive_status`、`/proactive_pause`、`/proactive_resume`、`/proactive_once`。这些命令需要 AstrBot admin 权限，用于查看队列、暂停/恢复后台 worker、手动处理一个任务。

后续模块会按社区插件方式拆分：

- `astrbot_proactive_core`：共享任务队列、并发控制、状态和错误脱敏。
- `astrbot_plugin_proactive_chat`：AstrBot 插件入口、QQ 群聊适配、上下文和主动消息策略。
- TTS / STT provider 插件：语音输入输出能力，优先复用 AstrBot 已启用 provider。
