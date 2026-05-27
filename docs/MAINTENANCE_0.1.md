# 0.1.x 维护策略

`0.1.x` 的目标是让首个社区插件稳定安装、稳定加载、稳定完成 QQ 文本最小链路。不要在这个版本线继续扩张大功能。

## 允许进入 0.1.x 的修复

- PyPI package metadata 或 wheel 内容错误。
- AstrBot 插件入口加载失败。
- `metadata.yaml`、`_conf_schema.json`、`requirements.txt` 与真实版本不一致。
- QQ 群聊文本事件无法解析。
- `/proactive_status`、`/proactive_pause`、`/proactive_resume`、`/proactive_once` 崩溃。
- 队列数据库无法创建或任务状态错误。
- LLM provider 调用适配错误。
- TTS/STT provider 调用适配错误。
- 主动发送失败时未正确记录 delivery state。
- 错误信息泄露 token、Authorization、签名 URL 或本地敏感路径。

## 不进入 0.1.x 的需求

- 长期 memory。
- WebUI。
- Telegram 正式支持。
- Discord 正式支持声明。
- 视觉理解。
- 游戏控制。
- 桌面/直播事件控制。
- 新建多个 TTS/STT provider 插件。

这些需求进入 v0.2 或更远路线。

## 版本规则

- patch 版本只做兼容修复和安装修复。
- 如果 PyPI 已发布错误版本，不覆盖旧版本，直接发下一个 patch。
- README 和 `metadata.yaml` 推荐版本必须指向最新可安装 patch。
- GitHub Release 应只推荐最新 patch，旧版本保留历史说明。

## 回归门禁

每个 0.1.x 发布前必须跑：

```bash
uv run python scripts/smoke_check.py
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv build
```

还必须做干净 PyPI 安装验证：

```bash
uv venv /tmp/proactive-chat-install-check/.venv
uv pip install --refresh-package astrbot-plugin-proactive-chat --python /tmp/proactive-chat-install-check/.venv/bin/python astrbot-plugin-proactive-chat==目标版本
```

验证点：

- 自动安装 `astrbot-proactive-core>=0.1.0,<0.2.0`。
- wheel 包含 `main.py`。
- wheel 包含 `metadata.yaml`。
- wheel 包含 `_conf_schema.json`。
- wheel 包含 `requirements.txt`。
- `import main` 成功。
- 文件型 SQLite 队列能写入一条测试 job。

## 0.1.6 候选条件

如果只修 `metadata.yaml` 版本号或 README 上架说明，可以先不立即发版；但如果 AstrBot 社区插件索引直接读取 PyPI wheel 内的 `metadata.yaml`，则应发布：

```text
astrbot-plugin-proactive-chat==0.1.6
```

候选内容：

- `metadata.yaml` version 同步到 `v0.1.6` 或新的发布版本。
- README 安装说明固定推荐 `0.1.6+`。
- 社区上架文档进入仓库。
