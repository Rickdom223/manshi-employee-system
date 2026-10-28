# 满氏吉他制琴有限公司企业员工管理系统 V3.0

> 2026-10-28 后续调整：删除员工性别属性，页面、API与数据库均移除；原有其他数据保留。详见 docs/REMOVE-GENDER-20261028.md。

> **2026-10-28 初始数据已重建。** 当前仅有一个系统管理员 admin；按用户Word导入30名员工（27在职、3离职），HR为李名，四部门主管已绑定，电话与税前月基本工资按文档保存。在职基本工资合计222,900.00元。demo_admin、ljm和旧演示业务均不在当前库。详见 [本轮数据、账号和重建说明](docs/INITIAL-DATA-20261028.md)。
已实现前后端、持久化模型与Alembic迁移、完整API、网页和自动化测试。包含四个固定部门、员工姓名自动开户、四角色、离职复职治理及右侧顶部多标签页。

本轮验收：41项后端测试、9组新数据与19组原业务浏览器场景通过，前端类型检查与构建通过。重建明细见 docs/INITIAL-DATA-20261028.md。详见 [V3验收结果](docs/V3-ACCEPTANCE.md)、[主要API与修改文件](docs/V3-IMPLEMENTATION.md)。

唯一业务基线是项目根目录 `SPEC.md`（V3.0，2026-10-27）。旧资料保存在 `docs/history-v1/` 和 `docs/history-20261026/`，不作为运行或验收依据。

## 1. 环境

- Python 3.11+（本机验证 Python 3.13.7）。
- Node.js 22.12+，配套 npm（本机验证 Node 24.22.1）。
- SQLite 文件存储，不需要 Redis 或其他服务。
- 浏览器支持现代 JavaScript；自动化浏览器测试使用 Playwright。

以下命令均从项目根目录执行，特殊说明除外。建议仅使用一个开发服务器操作同一数据库。

## 2. Windows 首次安装

PowerShell：

```powershell
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Push-Location frontend
npm ci
Pop-Location
Push-Location backend
& .venv/Scripts/python.exe -m app.scripts.setup_env
& .venv/Scripts/python.exe -m app.scripts.init_db
Pop-Location
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

打开 `http://127.0.0.1:3000`。后端默认 `127.0.0.1:8000`；浏览器请求均发送到同源 `/api`。停止时在启动终端按 Ctrl+C，脚本会停止自己启动的后端。

本机已有虚拟环境、依赖与升级后的数据库，直接执行最后一条启动命令即可。已有 `backend/.env` 不会被配置生成器覆盖。

## 3. Linux / CloudStudio 首次安装与开发

现已配置一键启动，环境要求 Python 3.11+、Node.js 22.12+ 和 npm。在 CloudStudio 打开项目根目录，执行：

```bash
sh start.sh
```

脚本自动安装依赖，首次生成前后端配置，备份已有数据库，执行保留数据的升级，再同时启动后端8000和前端3000。按Ctrl+C停止本次启动的服务。原入口 `bash scripts/start_cloudstudio.sh` 继续有效。

在 CloudStudio 的端口面板选择 **3000** 并打开平台实际生成的预览地址；运行按钮已指向同一个启动入口。预览域名从平台环境识别，缺少环境变量时可传 `--preview-url '平台实际HTTPS地址'`。同源代理保留Host、Cookie与CSRF校验。详细说明见 [CloudStudio一键启动](docs/CLOUDSTUDIO-ONE-CLICK.md)。

保留当前新增员工和打卡时使用 `manshi-cloud-current-data-日期时间.zip` 私密迁移包；首次导入自动核对数据库清单。只上传源码则按初始30人建库。重复启动不会重建或覆盖业务数据。

也可开两个终端：

```bash
# 终端一，项目根目录
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 终端二，项目根目录
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

## 4. 当前初始账号与业务演示

1. 系统管理员唯一为 `admin / Admin123`，不占员工名额。员工工号为1～30，姓名账号初始密码为`Aa123`。
2. HR为 `李名 / Aa123`，可直接维护职位、员工、考勤规则和工资；四位主管为汪维、杜硕、满园、高子象，均使用姓名登录并已绑定各自部门。
3. 普通员工例如 `韩涛 / Aa123`，可查看本人电话、税前月基本工资及个人业务。许卓、唐悠、冯敏已经离职，账号停用，无法登录。
4. 首次空库执行初始化默认安装这30人数据，重复启动不会覆盖已经修改的密码或业务。仅在设置`INITIAL_DATA_MODE=empty`时首次安装为空白模式，可使用首位HR引导流程。
5. 文档金额为月基本工资，已在员工档案和薪资参考区展示；没有虚构某个工资月份的最终实发记录。HR仍可按原流程录入按月最终薪资。
6. 管理员可管理角色与账号、指派主管。HR办理复职后需管理员启用原账号，高权限不会自动恢复。所有用户在账号设置中按原规则改密。

## 5. 从空库重新导入本轮数据

停止后端后，在项目根目录执行：

```powershell
# Windows：明确重建，当前业务会被备份后替换
& backend/.venv/Scripts/python.exe scripts/reset_initial_data.py
```

```bash
# Linux
backend/.venv/bin/python scripts/reset_initial_data.py
```

流程为：预校验源数据，在独立空库建立全部数据并校验，备份当前数据库，再原子替换。旧数据不合并。输入或候选库失败时不修改当前库。实际执行结果见 `docs/initial-data-reset-results.json`，备份保存在 `backend/backups/before-approved-roster-时间-标记.sqlite3`。

本轮已实际执行，之后的正常启动无需再次重建。重建只通过命令行提供，网页不提供清空数据库入口。旧版`upgrade_local_v3.py`属于保留旧数据的升级工具，不用于本轮重新填表；旧版文档仅供历史参考。

## 6. 配置

真实配置存放 `backend/.env`；根目录与后端的 `.env.example` 内容相同。运行 `setup_env` 会生成随机密钥，不覆盖既有文件。

| 配置 | 说明 |
|---|---|
| `SESSION_SECRET_KEY` | 至少32字符随机值；兼容旧 `APP_SECRET_KEY` / `JWT_SECRET_KEY` |
| `DATABASE_URL` | 默认 `sqlite:///./data/manshi.sqlite3`，相对路径相对于 backend |
| `DATABASE_PATH` | 可选绝对路径，优先于 DATABASE_URL，适合持久化挂载目录 |
| `BUSINESS_TIMEZONE` | 默认 `Asia/Shanghai`；服务器打卡与统计使用此时区 |
| `INITIAL_DATA_MODE` | 默认roster：本轮确认的30人数据；empty：仅四部门与admin（独立测试/手工建档） |
| `SESSION_EXPIRE_HOURS` | 默认8，范围1～168 |
| `COOKIE_SECURE` | HTTP本地用false；HTTPS部署用true |
| `ALLOWED_ORIGINS` | 额外明确允许的来源，逗号分隔；同源 Host 自动核验 |
| `APP_SERVE_STATIC` | true时由FastAPI提供frontend/dist与SPA回退 |
| `API_PROXY_TARGET` | Vite后端代理目标，默认http://127.0.0.1:8000；一键启动自动设置 |
| `VITE_API_BASE_URL` | 前端.env中的API前缀，默认/api；不使用记账本示例的/api/v1 |
| `CLOUDSTUDIO_PREVIEW_URL` | 可选，平台实际预览地址；一键启动也可从X_IDE_SPACE_*变量识别 |
| `PUBLIC_PORT` | 部署脚本使用的公开端口，默认8080 |

数据库文件应位于持久化目录。不要更换已在用系统的业务时区来解释既有打卡。生产环境务必保管 `.env` 和备份，首次登录后修改初始密码。

## 7. 构建并同源部署

推荐课程演示使用已验证的 FastAPI 同源方式：

```bash
cd frontend
npm ci
npm run build
cd ..
bash deploy/start-fallback.sh
```

CloudStudio 转发 **8080**。后端同时提供 `/api` 和构建后的网页，直接刷新 `/hr/employees` 等路径返回SPA。不存在的 `/api/...` 保持JSON 404。

Windows 同源方式：

```powershell
Push-Location frontend
npm run build
Pop-Location
$env:APP_SERVE_STATIC='true'
Push-Location backend
& .venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

具备 Nginx 的 Linux 环境也可执行 `bash deploy/start-cloudstudio.sh`；模板 `deploy/nginx.conf` 将 `/api` 代理至 FastAPI，并用 `try_files` 处理SPA刷新。脚本生成绝对路径配置并先执行 `nginx -t`。HTTPS预览来源与代理Host应保持一致，配置COOKIE_SECURE=true。**当前验证环境为Windows，未实际连接CloudStudio工作空间，也未运行Linux Nginx；已实测Vite代理和FastAPI同源部署。**

## 8. 测试

```powershell
# Windows，项目根目录
Push-Location backend
& .venv/Scripts/python.exe -m pytest -q --junitxml=../docs/v3-pytest-results.xml
Pop-Location
Push-Location frontend
npm run build
npm run test:e2e
Pop-Location
& backend/.venv/Scripts/python.exe scripts/verify_v3_deploy.py
```

```bash
# Linux，项目根目录
cd backend
.venv/bin/python -m pytest -q --junitxml=../docs/v3-pytest-results.xml
cd ../frontend
npm run build
npx playwright install chromium
npm run test:e2e
cd ..
backend/.venv/bin/python scripts/verify_v3_deploy.py
```

浏览器测试脚本自动建立独立临时数据库并启动服务，不修改正式库。Windows默认使用已安装Edge，可用 `E2E_BROWSER_CHANNEL=chrome` 指定Chrome；Linux默认使用Playwright Chromium。`PYTHON` 可指定已安装后端依赖的解释器。没有安装浏览器时先执行相应 `npx playwright install`。

`pytest.ini`仅收集 `test_v3_*.py`。旧版两角色与旧接口测试保留用于历史参考，不参与V3验收。现行测试与结果见 `docs/V3-ACCEPTANCE.md`。

## 9. 常见问题

- **401**：先重新登录；密码修改、角色修改、停用、离职会主动撤销会话。不要把401当成普通网络失败。
- **403 / CSRF**：浏览器统一使用网页同源 `/api`，检查代理是否保留Host、Origin是否匹配。自建代理域名不一致时在ALLOWED_ORIGINS中明确配置可信来源。
- **HTTPS登录后丢Cookie**：检查Secure配置、HTTPS转发与浏览器实际地址；HTTP开发环境不要使用Secure=true。
- **刷新业务路由404**：开启APP_SERVE_STATIC或使用Nginx的SPA回退；不要直接把前端源码目录作为静态目录。
- **导入错误**：下载系统模板，保留第一张表的前五列中文表头；部门与职位必须已存在。最大5MB、1000行，逐行返回成功/失败，不覆盖已有工号。
- **无法审批**：账号必须是当前负责该部门的主管，且申请不是本人提交；HR和管理员没有代批权限。
- **复职仍不能登录**：HR恢复档案后仍需管理员启用原账号。高权限不会自动恢复。
- **无规则或出勤率为—**：没有生效考勤规则或统计分母为零。先由HR新增规则版本。

## 10. 当前范围

九项人事功能、四角色、六类看板和内部多标签页均实现。职位停用和员工离职归档保留历史，不提供员工物理删除。首版仅SQLite；ORM与金额模型可复用，但尚未验证PostgreSQL部署。请假按整工作日，无小时/半天粒度，工作日由规则配置，不包含独立的法定节假日表。制琴生产任务、库存采购、销售订单、税费社保和硬件考勤不在V3范围；旧版相关代码未挂载到当前API与导航。

## 当前全员上下班打卡测试

运行 `backend/.venv/Scripts/python.exe scripts/test_all_employee_punches.py`，使用当前实际数据库的只读快照，在隔离副本逐个进行网页上班/下班打卡、顺序/重复/身份拦截和重启持久化检查；不写入实际考勤、不修改实际账号密码。逐人报告见 [全员打卡测试](docs/all-employee-punch-results.md)。

## 当前页面可见的短班次演示

本轮按用户明确要求，已在当前系统保存2026-10-28的2分钟班次（14:28:40～14:30:40，0容忍），并展示韩涛正常、吴琪迟到、孙颖早退、林墨缺下班卡、赵欣缺勤、周可获批请假。详见 [当前短班次效果](docs/SHORT-ATTENDANCE-DEMO.md)。此前的全员隔离测试报告不代表当前库数据；本次演示实际写入当前库。
