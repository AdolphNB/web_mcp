# 保持现有功能的安全加固

本批次保留页面内容、工具目录、新闻发布流程、管理令牌、API 路径与返回结构。
也保留现有 PV / API 统计口径，不自动删除数据库日志、不修改历史计数。
工具执行功能、目录分页、新闻修订恢复等会改变产品行为或数据结构的事项不属于本批次。

## 已实现的步骤

1. 部署不再以 root `source .env`，由 python-dotenv 读取配置数据。
   应用代码、虚拟环境与 `.env` 由 root 持有，www-data 只有读取/执行权限。
   SQLite 运行数据位于 `/var/lib/mcptools`，日志仍位于 `/var/log/mcptools`。
2. `uv.lock` 随代码部署，使用 `uv sync --locked --no-dev`，锁文件过期时部署失败，避免静默换版本。
3. API 日志的同步数据库操作移入线程池，写入失败不影响正常 API 返回，也不输出含请求参数的异常内容。
   仍然等待写入结束以保持现有统计可见性；这不是异步队列，数据库缓慢时单个请求仍可能等待。
   不可信路径、IP 和 User-Agent 按数据库字段容量截断。
4. Nginx 按客户端地址共享限流：页面/API 30 次/秒、突发 120；管理 API 额外 5 次/秒、突发 30。
   超限返回 JSON 429 和 `Retry-After: 1`；静态资源和健康检查不占额度。
   只在安装新 Nginx 配置后生效，不能用应用开发服务器替代公网入口。
5. 公开 API 默认继续允许任意来源，但不开放跨域 Cookie 凭据。
   管理 API 默认不开放跨域；同源 Swagger 与 MCP/服务器调用继续可用。
   若已有独立域名的管理前端，在部署前配置 `SITE_ADMIN_CORS_ORIGINS=https://admin.example.com`。
   多个来源用逗号分隔，必须包含协议和端口（若非默认端口），不能使用 `*`。
   修改 CORS 环境变量后需重启应用。
6. 新增 `nosniff`、同源嵌入限制、Referrer Policy 与基础 CSP。
   CSP 限制 base/object/嵌入来源，没有限制现有脚本和样式，保留首页及 Swagger 兼容性。
   这是基础防护，尚未启用严格 script-src 的 XSS 缓解策略。
7. 生产部署验证证书链、两个域名及至少一天的剩余有效期。
   缺失或无效证书时在停机前退出。只有显式 `ALLOW_SELF_SIGNED_CERT=1` 才允许本地自签名测试。
   此开关直接传给部署命令，不放在 `.env`；生产不要使用它。
8. Gunicorn access/error 日志每日轮转、保留 14 份并压缩；Supervisor 保持原有轮转设置。

## 部署前

- 在可信代码检出目录执行，先备份实际数据库、`.env` 与现行 Nginx 配置。
- 安排维护窗口。脚本会停止 Supervisor 中的 mcptools，再安装依赖和迁移位置。
  其他手工启动的同库进程也必须停止。失败时应用可能保持停止，不会假装发布成功。
- 首次部署先通过现有 ACME/DNS 验证流程申请证书，放到
  `/etc/letsencrypt/live/singularitynear.com/{fullchain.pem,privkey.pem}`。
  证书应覆盖 `singularitynear.com` 与 `www.singularitynear.com`，保留有效的续期任务。
- 检查是否有独立管理前端，并按上文设置 CORS 来源。
- 若入口有 CDN/负载均衡，先只对可信代理配置 Nginx real_ip；否则不同访客可能共用代理 IP 的限额。
  不要把任意客户端发送的 X-Forwarded-For 直接当作限流身份。

## SQLite 兼容处理

部署脚本读取 `.env`：在项目目录内的 SQLite 文件通过 SQLite backup API 复制至独立数据目录，
包括已提交的 WAL 内容。完整性检查通过后才修改 DATABASE_URL，原数据库不删除。
外部 PostgreSQL 和位于项目目录外的 SQLite 配置保持不变。
外部 SQLite 的目录必须已对 www-data 开放必要写权限。
SQLite URI 配置需要人工迁移；脚本拒绝自动处理。

已有目标文件或 `.pending` 文件时拒绝覆盖。若上次复制完成但写入 `.env` 失败，
先核实目标数据完整性，再将 `.env` 指向已核实的绝对路径；不要删除目标文件后盲目重试。

## 部署与验证

在项目根目录执行 `sudo bash deploy.sh`。完成后检查：

```bash
sudo nginx -t
sudo supervisorctl status mcptools
curl --fail https://singularitynear.com/health
curl --fail https://singularitynear.com/tools
curl --fail https://singularitynear.com/openapi.json
sudo logrotate --debug /etc/logrotate.d/mcptools
```

同时验证新闻草稿/发布、管理查询、页面复制按钮和移动端导航。
限流压测应在预发布环境进行，确认 429 及 Retry-After，不要压测生产站点。
数据库日志仍会增长；保留期限需结合统计口径决定，本批次没有自动清理历史数据。

## 回退

优先回退应用代码和 Nginx 配置，继续使用 `.env` 中的新数据库绝对路径；
旧版代码同样支持 DATABASE_URL，因此无需把数据迁回代码目录，也无需恢复可写代码权限。
如发布后已经产生新数据，不要直接切回保留的旧 SQLite 文件，否则会丢失这些新写入。
仅在确认没有新写入或完成数据合并后，才考虑恢复数据库备份。

自动化验证覆盖已有功能、CORS、安全响应头、线程池日志、日志故障隔离，以及 WAL 迁移/重复执行/拒绝覆盖。
本地 Windows 测试不能替代目标 Linux 上的 Nginx、Supervisor、文件权限和证书续期检查。
