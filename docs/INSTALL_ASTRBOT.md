# AstrBot 实机安装验证

本文档用于验证 `astrbot-plugin-proactive-chat==0.1.6` 在真实 AstrBot 环境中的最小可用链路。

## 目标

- AstrBot 能识别插件入口 `main.py`、`metadata.yaml` 和 `_conf_schema.json`。
- 插件能自动安装并加载 `astrbot-proactive-core>=0.1.0,<0.2.0`。
- QQ 群聊中能完成“观察消息 -> 入队 -> 手动处理 -> 主动回复”的最小链路。
- Discord 群聊可以作为实验通道验证文本链路；如果失败，先记录为兼容性问题，不阻塞 QQ v0。

## 前置条件

- AstrBot 版本 `>=4.8.0`。
- 已接入 QQ 平台，并能在测试群收发消息。
- AstrBot 当前 LLM provider 可用。
- 如果验证语音输入，需要 AstrBot 当前 STT provider 可用。
- 如果验证语音输出，需要 AstrBot 当前 TTS provider 可用。

## 安装方式

推荐先用 PyPI 安装当前稳定版本：

```bash
uv pip install astrbot-plugin-proactive-chat==0.1.6
```

该命令应自动安装：

```text
astrbot-proactive-core==0.1.0
```

如果 AstrBot 的插件管理器要求从 GitHub 安装，则使用：

```text
https://github.com/yurisachan16-creator/astrbot_plugin_proactive_chat
```

## 安全默认值检查

首次加载后，插件应保持安全关闭状态：

- `enabled_groups=[]`
- `proactive_enabled=false`
- `ambient_enabled=false`
- `background_worker_enabled=false`
- `voice_input_enabled=false`
- `voice_output_enabled=false`
- `quiet_hours_enabled=true`
- `kill_switch=false`

这一步通过后再开启测试群。

## QQ 最小验证流程

1. 在配置里只填一个测试群：

```text
enabled_groups=["测试群号"]
```

2. 打开文本观察和主动发言：

```text
ambient_enabled=true
proactive_enabled=true
background_worker_enabled=false
```

3. 在测试群发送一条普通文本消息。

4. 执行：

```text
/proactive_status
```

期望看到：

```text
队列: 可用
任务: queued>=1
worker: 可用
后台 worker: 未运行
```

5. 执行：

```text
/proactive_once
```

期望结果：

- 如果 LLM 和发送链路都正常：群里出现一条主动回复。
- 如果失败：任务应进入 failed 或 delivery_failed，错误细节不应暴露 token、URL 参数、Authorization 等敏感信息。

6. 再执行：

```text
/proactive_pause
/proactive_resume
```

期望插件不会抛异常，状态能正常切换。

## 语音验证流程

语音输入和输出不是 v0 上架阻塞项，但可以作为扩展验证。

1. 开启：

```text
voice_input_enabled=true
```

发送一条纯语音消息。期望它入队为 `voice_group_message`，并在处理时调用 STT。

2. 开启：

```text
voice_output_enabled=true
```

期望 worker 优先尝试 TTS + Record 音频发送；如果 TTS 或音频发送失败，应回退文本发送。

## 通过标准

QQ v0 通过需要满足：

- 插件能加载。
- 配置 schema 能显示。
- `/proactive_status` 可用。
- 文本消息能入队。
- `/proactive_once` 能至少完成一次 LLM + 文本主动发送。
- 失败时不泄露 provider token 或完整私密 URL。

Discord v0 通过标准较低：

- 插件不因 Discord 事件结构崩溃。
- 文本链路能观察到群消息或明确记录为待适配。

## 记录模板

```markdown
日期：
AstrBot 版本：
插件版本：0.1.6
core 版本：0.1.0
平台：QQ / Discord
LLM provider：
STT provider：
TTS provider：

结果：
- 插件加载：
- 配置 schema：
- /proactive_status：
- 文本入队：
- /proactive_once：
- 后台 worker：
- 语音输入：
- 语音输出：

问题：
- 
```

## 2026-05-27 QQ 实机记录

```markdown
日期：2026-05-27
AstrBot 版本：v4.23.2
插件来源：GitHub main
插件提交：ffc0198
插件版本：v0.1.6
core 版本：0.1.0
平台：QQ / aiocqhttp
测试群：892***726
LLM provider：AstrBot 当前默认 provider
STT provider：未测
TTS provider：未测插件语音输出；环境中另有 GPT-SoVITS 装饰插件会处理命令回复

结果：
- 插件加载：通过，AstrBot 日志显示 Plugin astrbot_plugin_proactive_chat (v0.1.6) by aitwo。
- 配置 schema/defaults：通过，配置文件生成并保持安全默认值；默认 enabled_groups=[]、proactive_enabled=false、ambient_enabled=false、background_worker_enabled=false、voice_input_enabled=false、voice_output_enabled=false、quiet_hours_enabled=true、kill_switch=false。
- 安装依赖：通过，astrbot-proactive-core==0.1.0 可 import；远端访问 PyPI 出现 SSL EOF，实机本次使用本地 wheel fallback 安装 core。
- /proactive_status：通过，输出包含“队列: 可用”“任务: queued=3”“worker: 可用”“后台 worker: 未运行”。
- 文本入队：通过，模拟 QQ 群普通文本后 jobs 从 0 增至 1，任务为 ambient_group_message / queued。
- /proactive_once：通过，最早的 ambient_group_message 从 queued 进入 completed/published，命令返回“已处理 1 个队列任务”。
- /proactive_pause：通过，返回“后台 worker 已暂停”。
- /proactive_resume：通过，返回“后台 worker 已启动”；验证后已再次执行 /proactive_pause，避免继续处理旧队列。
- 命令不入队：通过，v0.1.6 后 /proactive_status 前后 jobs 数量保持不变。
- 失败脱敏：通过，旧版本遗留命令任务因 cooldown_active 失败，公开字段只包含 cooldown_active；队列公开字段扫描未发现 Authorization、Bearer、cookie、token、api key、签名 URL、base64/audio payload 或本地路径。
- 语音输入：未测。
- 语音输出：未测。

问题：
- v0.1.2 到 v0.1.5 不建议上架：实机验证发现 AstrBot 包路径导入和命令入队问题，已在 v0.1.6 修复。
- 远端机器访问 PyPI 有 SSL EOF，不能证明 AstrBot 在该机上可自动从 PyPI 拉取 core；但 requirements.txt 与本地构建门禁通过，core wheel 安装和 import 已验证。
- 本次用 OneBot HTTP 事件模拟 QQ 群消息；真实 QQ/NapCat 连接在线，AstrBot aiocqhttp 已连接。
```
