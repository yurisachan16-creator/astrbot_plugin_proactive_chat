# AstrBot 社区上架材料

## 推荐标题

主动消息（Proactive Chat）

## 一句话介绍

让 AstrBot 在 QQ 群聊中具备 AIRI-like 的主动消息能力，支持安全默认值、持久队列、管理命令和可扩展语音链路。

## 推荐版本

- 插件：`astrbot-plugin-proactive-chat==0.1.6`
- 核心库：`astrbot-proactive-core==0.1.0`

不要推荐 `0.1.0` 或 `0.1.1`：

- `0.1.0` 的 PyPI wheel 未声明 core runtime dependency。
- `0.1.1` 补了 dependency，但 wheel 未包含完整 AstrBot 插件入口文件。
- `0.1.6` 是首个完整可安装版本。

## 仓库和包

- 插件仓库：https://github.com/yurisachan16-creator/astrbot_plugin_proactive_chat
- core 仓库：https://github.com/yurisachan16-creator/astrbot_proactive_core
- 插件 PyPI：https://pypi.org/project/astrbot-plugin-proactive-chat/
- core PyPI：https://pypi.org/project/astrbot-proactive-core/

## 支持平台

当前 `metadata.yaml` 只声明：

```yaml
support_platforms:
  - aiocqhttp
```

Discord 已在设计目标内，但在没有完成实机验证前，不建议写成正式支持平台。

## 安全说明

插件默认不主动发言，也不监听任何群。用户必须显式配置：

- `enabled_groups`
- `ambient_enabled`
- `proactive_enabled`
- `background_worker_enabled`

语音输入和语音输出默认关闭，需要用户自己开启 STT/TTS provider 后再启用。

## 配置项摘要

- `enabled_groups`：允许主动聊天的 QQ 群号。
- `proactive_enabled`：允许主动发言。
- `ambient_enabled`：允许群文本消息进入队列。
- `background_worker_enabled`：允许后台 worker 自动处理队列。
- `voice_input_enabled`：允许语音消息进入 STT 链路。
- `voice_output_enabled`：允许回复时尝试 TTS 音频。
- `quiet_hours_enabled`：启用免打扰时间。
- `cooldown_seconds`：每群主动回复冷却。
- `daily_reply_limit`：每群每日主动回复上限。
- `queue_database_path`：SQLite 队列路径。
- `kill_switch`：紧急关闭主动聊天。

## 已知限制

- Telegram 尚未验证。
- Discord 尚未声明为正式支持平台。
- v0 不包含 WebUI。
- v0 不包含长期 memory。
- v0 不包含视觉、游戏或桌面控制。
- provider 插件拆分属于 v0.2 之后的路线。

## 上架前检查清单

- [x] `metadata.yaml` 版本与推荐安装版本一致。
- [x] README 中文安装说明指向 `0.1.6`。
- [x] `docs/INSTALL_ASTRBOT.md` 已完成一次 QQ 实机记录。
- [x] PyPI 页面能显示 `astrbot-plugin-proactive-chat==0.1.6`。
- [ ] GitHub Release `v0.1.6` 可访问。
- [ ] 截图包含配置页和 `/proactive_status` 输出。
