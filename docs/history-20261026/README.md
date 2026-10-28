# 满氏制琴｜员工管理平台

FastAPI + Vue 3 的可运行课程项目。全部 P0 接入 SQLite，示例人员、组织及技能资料均为虚构。没有考勤、工资、MES、Cookie 登录或刷新令牌。

## 快速使用当前 Windows 工作区

本次已安装依赖、生成仅本机可见的 `backend/.env` 并完成幂等初始化。浏览器打开 `http://127.0.0.1:3000`。管理员用户名与随机初始密码在 `backend/.env` 的 `INITIAL_ADMIN_USERNAME`、`INITIAL_ADMIN_PASSWORD` 中查看，请勿分享该文件。

服务未运行时，在本目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

如果提示端口占用，请关闭原来启动服务的终端后再运行，脚本不会抢占其他进程。Ctrl+C 结束前端并清理该脚本启动的后端。

## 首次安装：CloudStudio / Linux

使用 Python 3.11+、Node 22.12+（建议 Node 24 LTS，附带 npm）。上传完整源码并把工作空间根目录设为本项目根目录。

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock.txt
cd backend
.venv/bin/python -m app.scripts.setup_env
# 在本机编辑 .env，查看并按需要替换初始管理员密码；不要提交此文件
.venv/bin/python -m app.scripts.init_db
cd ../frontend
npm ci
cd ..
bash scripts/start_cloudstudio.sh
```

也可复制 `backend/.env.example` 为 `backend/.env` 后手工配置。程序拒绝短密钥及占位密钥；新建管理员时拒绝短于12字符、超过256字符、占位或与用户名相同的密码。推荐使用生成脚本提供的随机值。环境变量优先于 `.env`。

CloudStudio 只预览 **3000**；8000 保持 `127.0.0.1` 内部监听。配置文件为 `.vscode/preview.yml`。云端实际 URL、端口可见性和外部分享尚需在平台验证，详见 [部署说明](docs/cloudstudio-deploy.md)。

## 首次安装：Windows

在本项目根目录执行：

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt
cd backend
.venv/Scripts/python.exe -m app.scripts.setup_env
.venv/Scripts/python.exe -m app.scripts.init_db
cd ../frontend
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

此电脑没有系统 npm，开发过程中下载的 npm 10.9.2 位于忽略的 `.tools/package`，当前工作区可将 `npm ...` 替换为 `node ../.tools/package/bin/npm-cli.js ...`（在 frontend 目录）。这个辅助运行时不包含在源码交付包；其他电脑安装官方 Node 即可使用其 npm。

## 分别启动两个进程

Linux，终端 A：

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

终端 B：

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

Windows 的终端 A 将 Python 路径改为 `.venv/Scripts/python.exe`；终端 B 命令相同。浏览器全部 API 请求发往当前 origin 的 `/api`，Vite 原样转发到 8000，`/health` 同样代理。不需要 CORS 通配配置。

## 配置

| 变量 | 用途 |
| --- | --- |
| JWT_SECRET_KEY | 至少32字符的高强度随机密钥；必填 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 1–1440，默认30分钟 |
| INITIAL_ADMIN_USERNAME | 初始化用户名，默认 demo_admin |
| INITIAL_ADMIN_PASSWORD | 仅首次创建该管理员使用；重复初始化不会重设密码 |
| DATABASE_PATH | 可选绝对路径；默认固定为 backend/data/manshi.sqlite3 |
| __VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS | 如预览 Host 被拒绝，仅加入平台实际准确主机名，不含协议/路径 |

`init_db` 可以重复运行，不覆盖已有员工、管理员密码或字典。启动脚本不建表也不删除数据库。更改 `.env` 中的初始密码不会修改已经存在的管理员。不要公开 `.env`、数据库或备份。

## 测试与构建

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
cd ../frontend
npm ci
npm run build
npm audit
# 先启动两个服务，安装 Chrome 或 Edge；测试只使用虚构演示数据
npm run test:e2e
# 若使用 Edge：E2E_BROWSER_CHANNEL=msedge npm run test:e2e
cd ..
backend/.venv/bin/python scripts/verify_persistence.py
```

Windows 将 `.venv/bin/python` 换成 `.venv/Scripts/python.exe`。Edge 测试可先设置 `$env:E2E_BROWSER_CHANNEL='msedge'`。浏览器测试读取本地 `.env`，通过 UI 新增演示记录并归档，不清除已有数据；每次运行会留下少量清楚标注的测试记录。自动化后端测试使用 pytest 临时数据库，不污染演示库。

本次实测环境：Python 3.13.7、Node 24.14.0、npm 10.9.2；FastAPI 0.115.12、SQLAlchemy 2.0.40、Pydantic 2.11.4；Vue 3.5.44、Vite 6.4.5、Element Plus 2.14.7、Axios 1.20.0、Vue Router 4.5.1、Playwright 1.64.1。完整 Python 版本在 requirements-lock.txt，前端传递依赖在 package-lock.json。依赖版本由本次安装与测试固定，不表示未来无新漏洞。

## 备份与恢复

```bash
cd backend
.venv/bin/python -m app.scripts.backup_db backups/manshi-backup.sqlite3
```

在线备份使用 SQLite backup API 并检查完整性，不覆盖已有目标。先恢复到另一个路径：停止服务，将副本复制到新的受控位置，设置 `DATABASE_PATH` 为该副本绝对路径，再启动；确认数据正确后才决定是否切换原库。`verify_persistence.py` 自动生成临时恢复副本并两次重启独立进程检查人数，不覆盖原库。

## 故障排查与边界

- `/health` 在3000应为200 JSON；`/api/employees` 未登录应为401 JSON；若是 HTML，检查 Vite 代理及后端路径，不能删除 `/api` 前缀。
- 连接失败先检查8000进程、启动错误和数据库是否已初始化。3000或8000占用时明确失败，不自动换端口。
- `Blocked request` 按部署文档加入准确 Host，禁止 `allowedHosts: true`。CloudStudio 中不要把浏览器 API 指向 localhost:8000。
- 刷新后回到登录页是预期行为；令牌只在内存，不写 localStorage/sessionStorage，不使用 Cookie。退出清除内存令牌；旧 JWT 在到期前仍可能有效，尚无服务端撤销。
- 登录限流为单进程内每来源IP每分钟10次，进程重启会清空；同源代理可能让多个用户共享来源IP。不是分布式防暴力破解系统。
- 构建成功但 Element Plus 供应商包仍有超过500kB提示；这是课程桌面项目的已知性能限制。后端测试有一条第三方 AnyIO 弃用警告，不影响通过。
- Vite 仅用于临时课程演示，不保证永久在线，不能公开真实员工数据。本次未完成 CloudStudio 平台部署。

进一步资料：[操作手册](docs/user-manual.md)、[接口与规则](docs/spec.md)、[架构](docs/architecture.md)、[验收清单](checklist.md)、[审查报告](docs/review.md)、[真实测试记录](docs/test-results.md)。
