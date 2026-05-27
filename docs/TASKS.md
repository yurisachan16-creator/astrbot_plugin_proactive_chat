# 下一阶段任务清单

## P0：实机安装验证

- [x] 在真实 AstrBot 环境安装 `astrbot-plugin-proactive-chat==0.1.6`。
- [x] 确认 `astrbot-proactive-core==0.1.0` 可安装并 import。
- [x] 确认 AstrBot 插件列表能识别“主动消息”。
- [x] 确认 `_conf_schema.json` 默认值能生成安全配置。
- [x] QQ 测试群执行 `/proactive_status`。
- [x] QQ 测试群发送文本消息并确认 queued 增加。
- [x] 执行 `/proactive_once` 并确认任务 completed/published。
- [x] 执行 `/proactive_pause` 和 `/proactive_resume`。
- [x] 记录一次失败场景，确认错误不泄露敏感信息。
- [x] 发布 `astrbot-plugin-proactive-chat==0.1.6` 到 PyPI。
- [x] 从 PyPI 干净安装 `astrbot-plugin-proactive-chat==0.1.6`，确认自动安装 core 并包含 AstrBot 入口文件。

## P1：社区上架

- [x] README 首页明确推荐 `astrbot-plugin-proactive-chat==0.1.6`。
- [x] 上架说明引用 `docs/COMMUNITY_LISTING.md`。
- [x] 准备 `v0.1.6` release notes。
- [ ] 准备配置页截图。
- [ ] 准备 `/proactive_status` 截图。
- [x] 完成一次 QQ 实机记录，并整理到 `docs/INSTALL_ASTRBOT.md` 和 `docs/RELEASE_0.1.6.md`。
- [x] 确认 `support_platforms` 暂只写 `aiocqhttp`。

## P1：0.1.x 修复

- [x] 判断是否需要发布 `0.1.7` 来修复 P0 实机验证发现的问题：目前不需要，`0.1.6` 已覆盖 P0 暴露的安装、导入和命令入队问题。
- [ ] 如果发布 `0.1.7`，必须重新跑干净 PyPI 安装验证。
- [x] 把旧版本说明写入 release notes，推荐用户使用最新 patch。

## P2：v0.2 设计

- [x] 固定 voice adapter 协议设计。
- [x] 设计 `/proactive_status` 的 STT/TTS provider 状态输出。
- [x] 设计 provider 插件模板仓库。
- [x] 决定第一个真实 provider 插件：本地 HTTP provider。
- [x] 写 v0.2 design doc，后续再进入实现。

## P2：v0.2 最小功能验收

- [x] 实现 STT/TTS provider status：available / missing / failed / disabled。
- [x] `/proactive_status` 输出 voice input/output 和 STT/TTS provider 状态。
- [x] status 输出脱敏，不暴露 token、Authorization、cookie、完整 URL、base64、本地路径。
- [x] 保持现有语音 worker 行为：STT 失败不调用 LLM，TTS 失败回退文本，投递失败不计入限流。
- [ ] 如需对外发版，发布 `0.1.7` 并重新跑干净 PyPI 安装验证。
