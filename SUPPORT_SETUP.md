# Hermes 在线客服

入口：`/contact`，所有页面右下角另有「在线咨询」。公司邮箱为 `304633698@qq.com`。

## 工作方式

访客发送问题 → 网站保存短期任务 → 本机的独立客服 worker 通过 HTTPS 领取 → 使用现有 Hermes Python 运行时调用模型 → 将回复交回网站。

无需开放本机入站端口。客服使用独立 `HERMES_HOME`，只复制模型配置与对应的模型 API 密钥，不加载原 Hermes 的 MCP、个人记忆或工作目录。每次咨询新建 AIAgent，`enabled_toolsets=[]`，并在接收访客输入前检查工具列表为空。因此客服不能管理新闻、执行命令或操作网站后台；原有管理网站的 MCP 配置继续独立使用。

回答依据为公司服务信息、最多 30 项上架工具和最近 3 条已发布新闻，草稿不会传入模型。界面保留最多 4 轮历史用于追问，刷新后开启新会话。未知信息和商务报价引导到邮箱，不会自动发邮件。

## 网站配置

1. 部署客服相关代码、模板及静态文件。
2. 在网站 `.env` 设置 `SITE_SUPPORT_WORKER_TOKEN`：至少 32 字符的独立随机令牌，不得使用 `SITE_ADMIN_TOKEN` 或 `SITE_ANALYTICS_TOKEN`。例如用 Python `secrets.token_urlsafe(48)` 生成，将结果安全保存，不提交 Git。
3. `SUPPORT_DAILY_LIMIT=200` 为全站每日上限；单 IP 每分钟 6 次、每天 30 次。以 UTC 日期计算，网关必须正确传递真实 IP，应用仅信任自己的反向代理。
4. 执行 `.venv/bin/python scripts/migrate.py migrate` 创建新增表，然后重启网站进程。不会清空原有数据。

## Worker 配置

所需环境：已经能调用模型的 Hermes Agent Python 环境，包含 `httpx`、`PyYAML` 和 `python-dotenv`。本次对接的是本机现有 Hermes 的 `deepseek` provider。此集成使用 Hermes Python 接口；升级 Hermes 后应重新验证兼容性。

将 `integrations/hermes/support_agent.py` 和 `support_worker.py` 放在同一目录。在仅当前用户可读的独立目录创建：

```text
website/
  support_agent.py
  support_worker.py
  config.json
  token                 # 专用 SITE_SUPPORT_WORKER_TOKEN
  profile/
    config.yaml         # 仅 model 配置，不添加 mcp_servers
    .env                # 仅模型凭据，如 DEEPSEEK_API_KEY
```

`profile/config.yaml` 的 `model` 复制现有 Hermes 的有效 `default`、`provider`、`base_url`、`api_mode`（后两项可省略）；不复制整个个人配置或 auth 文件。

`config.json` 示例（路径替换为实际安装位置）：

```json
{
  "site_url": "https://singularitynear.com",
  "token_file": "C:/Users/ThinkPad/AppData/Local/hermes/support/website/token",
  "profile": "C:/Users/ThinkPad/AppData/Local/hermes/support/website/profile",
  "hermes_python": "C:/Users/ThinkPad/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
}
```

启动命令：

```powershell
& "$env:LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe" `
  "$env:LOCALAPPDATA/hermes/support/website/support_worker.py" `
  "$env:LOCALAPPDATA/hermes/support/website/config.json"
```

保持一个 worker 实例。Windows 可使用用户登录启动项在后台运行；服务器可使用 Supervisor 或 systemd，并设置自动重启。Worker 每 5 秒领取任务，单次模型子进程最多运行 100 秒，期间维持心跳。程序日志仅记录是否成功，不记录访客问题、模型回复或令牌。

## 验证和维护

本次 Windows 安装目录为 `%LOCALAPPDATA%/hermes/support/website`，登录启动项为 `%APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup/HermesWebsiteSupport.vbs`。当前进程号保存在 `worker.pid`（仅本次启动，重启后以进程列表为准）；运行日志在 `worker.stderr.log`。启动项在隐藏窗口中运行，不会打开控制台。停用自动启动可移除该专用 VBS 文件；更新脚本后需重启对应的 `support_worker.py` 进程，避免同时启动多份。

- `GET /api/support/status` 的 `online` 表示最近 45 秒内收到 worker 心跳。
- 打开 `/contact` 发送一次真实咨询，确认回复完成；管理令牌不能调用客服 worker 接口，客服令牌也不能调用新闻管理接口。
- 本机休眠、关机或网络中断超过 45 秒，页面显示离线，常见问题和邮箱仍可使用。需要全天候在线时，将独立客服 worker 和模型配置迁移到常开服务器即可。
- 模型服务故障会返回联系邮箱的提示。在线心跳不代表模型服务一定可用。
- 任务超过 150 秒未完成即向访客显示失败。超过 7 天的客服记录在 worker 领取任务或新问题请求时清理；备份和模型供应商的保留策略应单独管理。
- 前端使用 `textContent` 展示回复，匿名会话随机标识只在当前页面内存中保存。不要将 worker 令牌或模型密钥放入网页、URL、Git 或截图。
- 自动测试：`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`。
