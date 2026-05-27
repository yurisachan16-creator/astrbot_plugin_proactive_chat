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
- [ ] 发布 `astrbot-plugin-proactive-chat==0.1.6` 到 PyPI。

## P1：社区上架

- [ ] README 首页明确推荐 `astrbot-plugin-proactive-chat==0.1.6`。
- [ ] 上架说明引用 `docs/COMMUNITY_LISTING.md`。
- [ ] 准备配置页截图。
- [ ] 准备 `/proactive_status` 截图。
- [ ] 完成一次 QQ 实机记录并附到 issue 或 release comment。
- [ ] 确认 `support_platforms` 暂只写 `aiocqhttp`。

## P1：0.1.x 修复

- [ ] 判断是否需要发布 `0.1.7` 来修复 P0 实机验证发现的问题。
- [ ] 如果发布 `0.1.7`，必须重新跑干净 PyPI 安装验证。
- [ ] 把旧版本说明写入 release notes，推荐用户使用最新 patch。

## P2：v0.2 设计

- [ ] 固定 voice adapter 协议。
- [ ] 给 `/proactive_status` 增加 STT/TTS provider 状态。
- [ ] 设计 provider 插件模板仓库。
- [ ] 决定第一个真实 provider 插件：本地 HTTP / OpenAI / Gemini。
- [ ] 写 v0.2 design doc 后再进入实现。
