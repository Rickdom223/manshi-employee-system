# CloudStudio 一键启动

在项目根目录运行：

```bash
sh start.sh
```

`bash start.sh` 和原入口 `bash scripts/start_cloudstudio.sh` 同样有效。CloudStudio 的运行按钮已配置为 `sh start.sh`，主预览端口为 **3000**。

## 环境与自动流程

工作空间需要 Python 3.11+、Node.js 22.12+、npm，并能下载 pip/npm 依赖。脚本会检查版本；环境不齐、安装失败或端口占用均停止并提示原因。

1. 建立 Linux Python 虚拟环境并安装锁定的后端依赖。
2. 首次生成 `backend/.env`（随机密钥）及 `frontend/.env`（`VITE_API_BASE_URL=/api`）；不覆盖已有配置。
3. 迁移包首次启动时核对全部业务表，备份现有数据库，再执行 Alembic 升级及幂等初始化。已有姓名账号、密码、角色、离职状态和业务数据均保留。
4. 自动执行 `npm ci`。锁文件及Node版本没有变化时复用已安装的前端依赖。
5. 启动后端 `127.0.0.1:8000`，健康检查通过后启动前端 `0.0.0.0:3000`，再验证网页、同源API代理和匿名访问拦截。

启动成功后，从 CloudStudio 端口面板打开 **3000** 的实际预览链接。接口文档位于同一网址的 `/api/docs`。Ctrl+C 或终止信号会停止本次启动的两个服务；任何一项服务意外退出，另一项也会停止。日志在 `deploy/runtime/cloudstudio-backend.log` 和 `cloudstudio-frontend.log`。

## 保留当前数据

使用 `manshi-cloud-current-data-日期时间.zip` 私密迁移包，其中包含 `backend/data/manshi.sqlite3` 和 `migration/manifest.json`。仅源码包会在空库初始化文档中的30名员工。迁移包清除云端副本的旧登录会话，账号密码保留，云端重新登录即可。

不要把含员工、联系电话、薪资和密码散列的迁移包提交到公开Git仓库；Git只提交源码，数据库在自己的工作空间单独上传。不要复制Windows `.venv` 或 `node_modules` 到Linux。启动脚本不会执行清空数据库的重建工具。

## 域名、代理和登录

当前项目保留实际使用的 `frontend/vite.config.js` 和 `frontend/src/api/http.js`，已按提供的范例完成配置，无需再添加一套未使用的 `vite.config.ts` 或 `request.ts`。本项目接口前缀是 `/api`，使用HttpOnly会话Cookie和CSRF校验。

脚本根据平台的 `X_IDE_SPACE_KEY`、`X_IDE_SPACE_REGION`、`X_IDE_SPACE_HOST` 识别预览地址，自动配置精确的Vite允许主机、HTTPS热更新及后端来源；HTTPS预览默认启用Secure Cookie。已有显式系统环境变量优先。

若工作空间没有这些变量，从端口面板复制真实地址后运行：

```bash
sh start.sh --preview-url 'https://这里替换为实际预览域名'
```

不需要填写后端绝对URL，不关闭Host或CSRF校验，不允许所有域名。平台域名变化后重新启动脚本。

## 检查与其他入口

### Ubuntu 在第4步退出

第4步失败意味着后端进程退出，前端3000尚未启动，应先查看 `tail -n 60 deploy/runtime/cloudstudio-backend.log`，不需要先开放8000公网端口。已修复Linux虚拟环境Python符号链接被误认作系统Python的启动问题。已安装依赖的旧副本可先在项目根目录执行 `backend/.venv/bin/python scripts/cloudstudio_start.py --skip-install`；更新启动脚本后继续使用 `sh start.sh`。如果仍然失败，按日志定位具体原因。

```bash
sh start.sh --check                 # 仅检查版本和端口
sh start.sh --prepare-only          # 安装依赖并准备配置、数据，暂不启动
sh start.sh --skip-install          # 已安装依赖时跳过安装
sh start.sh --check-startup         # 启动并验证后自动停止
```

调试时可用 `--backend-port` 和 `--web-port` 明确指定其他端口；平台预览配置也需同步。端口占用时脚本不会杀掉原服务或自动换端口。

原有构建网页的8080单端口方案保留在 `deploy/start-fallback.sh`，需先手工构建前端；与本次3000一键开发入口选择其一，不同时运行。

当前验证包括Windows上的真实前后端进程、代理和数据保留，以及shell入口语法。实际CloudStudio Linux工作空间、HTTPS网关、热更新和外部访问权限仍需部署时验收；本轮未执行云端部署。

2026-10-28本轮验证：51项V3回归测试、2项迁移快照测试通过；前端类型检查与构建通过；两个shell入口均在实际数据副本上完成启动与退出检查，业务数据及本机后端配置未改变。启动验证明细见 [结果文件](cloudstudio-startup-results.json)。

官方资料：[预览运行配置](https://cloudstudio.net/docs/guide/code_editing/basic_operations/how-to-run/)、[预览地址环境变量](https://cloudstudio.net/docs/guide/code_editing/FAQ/url-configuration/)、[Vite主机与代理配置](https://vite.dev/config/server-options)。
