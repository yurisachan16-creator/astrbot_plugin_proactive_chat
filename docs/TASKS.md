# 下一阶段任务清单

## P0：实机安装验证

- [ ] 在真实 AstrBot 环境安装 `astrbot-plugin-proactive-chat==0.1.4`。
- [ ] 确认自动安装 `astrbot-proactive-core==0.1.0`。
- [ ] 确认 AstrBot 插件列表能识别“主动消息”。
- [ ] 确认配置页显示 `_conf_schema.json` 字段。
- [ ] QQ 测试群执行 `/proactive_status`。
- [ ] QQ 测试群发送文本消息并确认 queued 增加。
- [ ] 执行 `/proactive_once` 并确认主动文本回复。
- [ ] 执行 `/proactive_pause` 和 `/proactive_resume`。
- [ ] 记录一次失败场景，确认错误不泄露敏感信息。

## P1：社区上架

- [ ] README 首页明确推荐 `astrbot-plugin-proactive-chat==0.1.4`。
- [ ] 上架说明引用 `docs/COMMUNITY_LISTING.md`。
- [ ] 准备配置页截图。
- [ ] 准备 `/proactive_status` 截图。
- [ ] 完成一次 QQ 实机记录并附到 issue 或 release comment。
- [ ] 确认 `support_platforms` 暂只写 `aiocqhttp`。

## P1：0.1.x 修复

- [ ] 判断是否需要发布 `0.1.5` 来修复 P0 实机验证发现的问题。
- [ ] 如果发布 `0.1.5`，必须重新跑干净 PyPI 安装验证。
- [ ] 把旧版本说明写入 release notes，推荐用户使用最新 patch。

## P2：v0.2 设计

- [ ] 固定 voice adapter 协议。
- [ ] 给 `/proactive_status` 增加 STT/TTS provider 状态。
- [ ] 设计 provider 插件模板仓库。
- [ ] 决定第一个真实 provider 插件：本地 HTTP / OpenAI / Gemini。
- [ ] 写 v0.2 design doc 后再进入实现。
