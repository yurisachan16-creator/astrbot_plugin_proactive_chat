# v0.1.6 Release Notes

`v0.1.6` 是 `astrbot-plugin-proactive-chat` 第一个建议社区用户安装的 patch 版本。

## 推荐安装

```bash
uv pip install astrbot-plugin-proactive-chat==0.1.6
```

依赖会自动安装：

```text
astrbot-proactive-core>=0.1.0,<0.2.0
```

如果通过 AstrBot 插件管理器从 GitHub 安装，使用：

```text
https://github.com/yurisachan16-creator/astrbot_plugin_proactive_chat
```

## 主要修复

- 修复 PyPI wheel 缺少完整 AstrBot 插件入口文件的问题。
- 修复 AstrBot 包路径导入场景下的相对导入问题。
- 修复 `/proactive_status`、`/proactive_pause`、`/proactive_resume`、`/proactive_once` 等管理命令被当作普通群消息入队的问题。
- README、`metadata.yaml`、`_conf_schema.json` 和 `requirements.txt` 已同步到 `0.1.6` 发布状态。

## 实机验证

已完成一次 QQ / aiocqhttp 实机验证：

- AstrBot 版本：`v4.23.2`
- 插件来源：GitHub main
- 插件版本：`v0.1.6`
- core 版本：`0.1.0`
- 平台：QQ / aiocqhttp
- 结果：插件加载、配置 schema、安全默认值、文本入队、`/proactive_status`、`/proactive_once`、`/proactive_pause`、`/proactive_resume` 均通过。
- 失败脱敏：公开输出未发现 token、Authorization header、cookie、完整签名 URL、base64/audio payload 或本地敏感路径。

完整记录见：

- `docs/INSTALL_ASTRBOT.md`

## 旧版本说明

不建议社区用户安装 `0.1.0` 到 `0.1.5`：

- `0.1.0` 未正确声明 core runtime dependency。
- `0.1.1` wheel 缺少完整 AstrBot 插件入口文件。
- `0.1.2` 到 `0.1.5` 在实机验证中暴露过 AstrBot 包路径导入和命令入队问题。

请直接使用 `0.1.6`。

## 已知限制

- 当前 `metadata.yaml` 只正式声明 `aiocqhttp`。
- Discord 和 Telegram 暂不作为正式支持平台。
- 语音输入/输出默认关闭，需要用户自行配置 AstrBot STT/TTS provider 后再启用。
- v0 不包含长期 memory、WebUI、视觉、游戏或桌面控制。

## 上架素材状态

- QQ 实机记录：已完成。
- PyPI 干净安装验证：已完成。
- GitHub Release：本 release。
- 配置页截图：待补。
- `/proactive_status` 截图：待补。
