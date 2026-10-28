# CloudStudio 部署及验收操作

状态：配置已生成，本机同源代理、浏览器流程已通过；**尚未在 CloudStudio 实际工作空间部署**。没有云端真实 URL、外部分享截图或平台可见性验证结果。本地证据不能替代平台验收。

## 1. 建立工作空间

选择同时包含 Python 3.11+、Node 22.12+ 与 npm 的 Linux 工作空间。上传源码包，展开后打开 `manshi-employee-system` 为工作空间根目录，能直接看到 backend、frontend、scripts、.vscode。不要上传本机 .venv、node_modules、.env 或数据库；Windows 虚拟环境不能在 Linux 直接复用。

## 2. 安装并初始化

在项目根目录：

```bash
python3 --version
node --version
npm --version
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock.txt
cd backend
.venv/bin/python -m app.scripts.setup_env
# 私下查看 .env 中生成的用户名和密码；严禁把内容贴到公开日志
.venv/bin/python -m app.scripts.init_db
cd ../frontend
npm ci
cd ..
```

如平台提供环境变量管理，可在那里设置 JWT_SECRET_KEY、INITIAL_ADMIN_USERNAME、INITIAL_ADMIN_PASSWORD，或使用后端目录的 .env；环境变量优先。不要使用示例占位值。初始化独立执行且幂等。遗忘既有管理员密码时，重新初始化不会覆盖原密码，不要反复修改初始化变量期待重置。

## 3. 启动与端口

运行 `bash scripts/start_cloudstudio.sh`，或者使用平台运行按钮读取 `.vscode/preview.yml`。脚本由自身路径定位根目录；预检查虚拟环境、Node/npm、依赖、密钥、数据库六表和端口；创建data目录但不删除旧库。后台启动8000并等待健康，前台运行固定3000的Vite。脚本退出 trap 只结束自己启动的后端PID。

`preview.yml` 仅配置 port:3000，mainPort:true。在端口面板预览3000，复制平台实际给出的HTTPS URL。8000仅内部监听；若平台仍自动发现8000，在面板设为“仅自己可见”。对3000是否公开，按教师访问需要明确选择，并实际验证。

不要自造工作空间 ID、端口域名或把 localhost:8000 放进前端。浏览器 localhost 是访问者自己的电脑。预览站点始终请求同域 /api/*，Vite不改写/api。

## 4. Host 与 WebSocket

若出现 Blocked request，先确认端口和平台实际 Host；必要时只设置实际主机名：

```bash
# 值由平台预览 URL 中的实际主机名替换，不包含 https:// 或路径
export __VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS='<实际准确预览主机名>'
bash scripts/start_cloudstudio.sh
```

不能设置 allowedHosts:true 或宽泛通配。HMR出错先检查浏览器 Network/Console 和网关 WebSocket规则，按证据作最小修改，不关闭Host校验。本机HTTP测试不能证明云网关HMR/HTTPS行为。

## 5. 验收与证据

先在工作空间终端执行：

```bash
curl -i http://127.0.0.1:3000/health
curl -i http://127.0.0.1:3000/api/employees
curl -i http://127.0.0.1:3000/
curl -i http://127.0.0.1:3000/employees/1
```

依次应为200健康JSON、401认证JSON、200 HTML、200 HTML。然后在实际3000 HTTPS预览页面：

1. 登录，Network确认 /api/auth/login 与 /api/employees 均使用当前域名，无CORS错误。
2. 新增虚构员工、编辑、关联两项技能、调整熟练度、技能筛选、离职归档，确认看板变化。
3. 刷新深层路由，资源不404并重新登录；Application确认无持久化令牌/Cookie登录。
4. 停止脚本后确认自己启动的后端退出；再次启动，确认已有员工保留。测试端口占用应失败，不能自动换端口或误杀别人进程。
5. 执行备份及恢复副本验证，详见README。不得为测试删掉演示库。
6. 在非工作空间登录态的另一浏览器或隐身窗口打开真实分享URL，记录是否要平台登录，按课堂需求调整可见性后再测试。

把截图存为 docs/screenshots/cloudstudio-*，在 checklist.md 记录执行命令、实际响应、真实URL和权限条件。截图不能带密码、JWT或配置密钥。

## 平台验收待填

| 项目 | 当前结果 |
| --- | --- |
| 实际3000 HTTPS URL | 未验证，待平台返回 |
| Python/Node/npm实际版本 | 未验证 |
| 平台运行按钮与preview配置 | 未验证 |
| Host允许列表/HMR | 未验证 |
| 8000端口权限 | 未验证 |
| 外部非工作空间登录态访问 | 未验证 |
| trap清理及信号行为 | Linux平台未验证 |
| 外部访问截图 | 未产生 |

空间停机、自动关机或权限变化会影响链接访问，不能宣称永久在线。Vite仅课程临时演示；不要上传真实员工资料。如需正式上线，应另行设计生产静态资源托管、同源代理、HTTPS、撤销/审计和运维方案。

官方资料：[preview.yml及主端口](https://cloudstudio.net/docs/guide/code_editing/basic_operations/how-to-run/)、[Vite server.proxy和allowedHosts](https://vite.dev/config/server-options)。
