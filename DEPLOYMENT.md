# mcptools.xin 部署指南

本部署脚本使用 **UV** 进行环境管理和依赖安装，同时解决权限问题，适用于生产环境。

## 问题背景

原问题：UV 创建的虚拟环境使用符号链接指向 `/root/.local/share/uv/python/...`，导致 www-data 用户无法访问，Supervisor 启动失败：

```
supervisor: couldn't exec /var/www/mcptools/.venv/bin/gunicorn: EACCES
```

## 解决方案

使用 UV 的以下选项强制使用系统 Python：

1. **`--python /usr/bin/python3`**：明确指定使用系统 Python 解释器
2. **`--no-managed-python`**：禁止 UV 下载或使用其管理的 Python 版本

这样创建的虚拟环境直接使用系统 Python，www-data 用户可以正常访问。

## 部署步骤

### 1. 首次部署

```bash
sudo ./deploy.sh
```

### 2. 重建虚拟环境（需要时）

如果需要重建虚拟环境（例如依赖变更）：

```bash
sudo ./deploy.sh --rebuild-venv
```

### 3. 仅重新部署（不重建 venv）

```bash
sudo ./deploy.sh
```

默认情况下，如果 venv 已存在，会跳过创建步骤，只复制新文件。

## 脚本说明

### deploy.sh

主部署脚本，完成以下步骤：

1. 安装系统依赖（python3, nginx, supervisor）
2. 确保 UV 已安装（如未安装会自动安装）
3. 创建项目目录和日志目录
4. 复制应用文件（使用 rsync 增量同步）
5. **使用 UV 创建虚拟环境（关键步骤）**
6. **使用 UV 安装项目依赖**
7. 配置环境变量（.env 文件）
8. 运行数据库迁移
9. 设置文件权限
10. 配置 Nginx
11. 配置 Supervisor
12. 启动服务

### setup-gunicorn.sh

配置 Supervisor 的辅助脚本：

1. 创建必要的目录
2. 验证虚拟环境存在且权限正确
3. 验证 Python 和 gunicorn 可执行
4. 复制 Supervisor 配置文件
5. 重载 Supervisor 配置

## UV 环境

### 虚拟环境创建

```bash
sudo -u www-data uv venv \
    --python /usr/bin/python3 \
    --no-managed-python \
    /var/www/mcptools/.venv
```

说明：
- `--python`：强制使用系统 `/usr/bin/python3`
- `--no-managed-python`：禁止 UV 管理的 Python，避免权限问题

### 依赖安装

```bash
sudo -u www-data uv pip install --no-dev
```

说明：
- 从 `pyproject.toml` 安装依赖
- `--no-dev`：跳过开发依赖

## 启动方式

### Supervisor 方式（推荐生产环境）

Supervisor 配置使用 venv 中的 gunicorn：

```
command=/var/www/mcptools/.venv/bin/gunicorn main:app -c /var/www/mcptools/deploy/gunicorn.conf.py
```

优点：
- 直接使用 gunicorn，性能最优
- 自动重启、日志管理
- 与 Supervisor 无缝集成

### 手动启动方式（开发/调试）

```bash
cd /var/www/mcptools
./.venv/gunicorn main:app -c deploy/gunicorn.conf.py
```

或使用 Uvicorn：

```bash
./.venv/uvicorn main:app --host 127.0.0.1 --port 8000
```

## 使用 UV run 启动（可选）

如果确实想使用 `uv run` 启动，可以修改 Supervisor 配置：

```
command=/var/www/mcptools/.venv/bin/uv run gunicorn main:app -c /var/www/mcptools/deploy/gunicorn.conf.py
```

但**不推荐**用于生产环境，因为：
- 额外的进程开销
- 增加故障点
- 性能略低

## 权限说明

### 文件所有者

- 项目目录：`www-data:www-data`
- 虚拟环境：`www-data:www-data`
- 日志目录：`www-data:www-data`
- PID 目录：`www-data:www-data`

### 目录权限

- 项目目录：`750`（仅 owner 可执行）
- 虚拟环境：`755`（所有用户可执行）
- 日志/ PID 目录：`755`

## 日志位置

- Supervisor 日志：`/var/log/mcptools/supervisor.log`
- 错误日志：`/var/log/mcptools/supervisor_error.log`
- Gunicorn 访问日志：`/var/log/mcptools/access.log`
- Gunicorn 错误日志：`/var/log/mcptools/error.log`
- Nginx 访问日志：`/var/log/nginx/mcptools-access.log`
- Nginx 错误日志：`/var/log/nginx/mcptools-error.log`

## 常用命令

### 查看 Supervisor 状态

```bash
sudo supervisorctl status mcptools
```

### 重启服务

```bash
sudo supervisorctl restart mcptools
```

### 停止服务

```bash
sudo supervisorctl stop mcptools
```

### 查看日志

```bash
# Supervisor 日志
sudo tail -f /var/log/mcptools/supervisor.log

# Gunicorn 错误日志
sudo tail -f /var/log/mcptools/error.log

# Nginx 访问日志
sudo tail -f /var/log/nginx/mcptools-access.log
```

### 更新 UV 依赖

```bash
cd /var/www/mcptools
sudo -u www-data uv pip install --no-dev
sudo supervisorctl restart mcptools
```

## 故障排查

### 服务启动失败

1. 检查 Supervisor 状态：
   ```bash
   sudo supervisorctl status mcptools
   ```

2. 查看错误日志：
   ```bash
   sudo tail -f /var/log/mcptools/supervisor_error.log
   ```

3. 测试 gunicorn 直接启动：
   ```bash
   cd /var/www/mcptools
   sudo -u www-data .venv/bin/gunicorn main:app -c deploy/gunicorn.conf.py
   ```

### 权限错误

重新设置权限：

```bash
sudo chown -R www-data:www-data /var/www/mcptools
sudo chmod 750 /var/www/mcptools
sudo chmod -R 755 /var/www/mcptools/.venv
sudo supervisorctl restart mcptools
```

### Python 版本问题

检查系统 Python 版本：

```bash
python3 --version
```

如果需要特定版本，修改 `deploy.sh` 中的 `SYSTEM_PYTHON` 变量。

## SSL/HTTPS 配置

部署完成后，可以使用 certbot 启用 HTTPS：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d mcptools.xin
```

## 优势

相比完全不使用 UV 的方案，本方案的优势：

1. **开发环境一致性**：本地开发和生产环境都使用 UV
2. **快速依赖安装**：UV 比 pip 快很多
3. **更好的依赖解析**：UV 的解析器更准确
4. **统一工具链**：一个工具管理所有 Python 相关任务
5. **无权限问题**：使用系统 Python，www-data 用户可访问
