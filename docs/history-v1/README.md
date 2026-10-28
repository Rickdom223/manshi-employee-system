# 满氏吉他制琴有限公司企业员工管理系统

依据根目录SPEC.md（2026-10-27多标签页版），在原FastAPI+Vue+SQLite工程上增量升级。原管理员、员工、部门岗位和多技能资料保留，新增考勤、请假、工资、员工端、制琴任务、质检与报表。没有公开注册功能。

## 当前本机登录与使用

打开 http://127.0.0.1:3000/login 。新规格账号：**ljm / Ljm123**。原demo_admin账号及其原密码保留；初始化不会覆盖修改过的密码。新账号首次登录后请在系统设置改密，新密码8–10位并包含大小写字母和数字。

点击左侧菜单打开/激活工作区标签；顶部可直接切换或关闭。首页常驻，关闭当前标签优先回左邻；重复打开不增加标签。筛选、滚动和表单输入保留，关闭有修改的标签会确认；退出或会话失效清空缓存。刷新通过Cookie恢复登录及当前账号的标签。

管理员九个一级模块：**首页概览、员工信息管理、部门与岗位管理、考勤管理、请假审批、薪资管理、制琴任务管理、统计报表、系统设置**。岗位和原制琴技能字典整合在部门模块的内部子页，未删除原技能功能。普通员工只有个人信息、个人考勤、请假申请、我的工资、我的任务、账号设置六页。

详细操作：[图文操作手册](docs/user-manual.md)。

## 已有工作区启动（Windows）

本次已备份旧库、执行迁移和初始化、安装依赖。服务关闭后可从本目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

端口占用时先关闭原服务终端。Ctrl+C停止该脚本并清理它启动的后端。不要删除backend/data或重新建立空数据库替代迁移。

## 新安装或更新：Windows

在项目根目录：

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt
cd backend
.venv/Scripts/python.exe -m app.scripts.setup_env
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.scripts.init_data
cd ../frontend
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

更新既有项目时先备份数据库，保留原.env；setup_env发现文件已存在会拒绝覆盖。迁移脚本保留原行、主键和密码哈希。新建库只有指定管理员、四个指定部门及制琴岗位，不自动插入员工业务数据；已有库保留额外历史部门。

## Linux本地开发

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock.txt
cd backend
.venv/bin/python -m app.scripts.setup_env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app.scripts.init_data
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另一终端：

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 3000
```

开发入口3000，/api与/health代理到内部8000，不改写/api。浏览器只访问前端origin。当前电脑无全局npm，项目忽略目录.tools中提供了开发时下载的npm10.9.2；在frontend目录可把 `npm ...` 替换为 `node ../.tools/package/bin/npm-cli.js ...`。交付包不带这个辅助运行时，其他电脑安装官方Node（自带npm）即可。

## 配置与认证

`.env.example`（根目录和backend中都有）复制到backend/.env或运行setup_env生成随机密钥。配置由backend/.env读取，系统环境变量优先。

| 配置 | 用途 |
| --- | --- |
| APP_SECRET_KEY | 必须为至少32字符随机值；兼容已有JWT_SECRET_KEY，作为CSRF派生密钥 |
| DATABASE_PATH | 可选绝对SQLite文件路径，优先于DATABASE_URL |
| DATABASE_URL | 可选SQLite URL；相对路径固定基于backend解析，默认data/manshi.sqlite3 |
| SESSION_EXPIRE_HOURS | 默认8小时，可配置1–168 |
| COOKIE_SECURE | 本地纯HTTP为false；HTTPS部署应为true |
| ALLOWED_ORIGINS | 写操作允许的准确origin列表，逗号分隔；CloudStudio填平台实际地址 |
| PUBLIC_PORT | CloudStudio默认8080，需与preview.yml同步 |

HttpOnly Cookie持有不可预测会话标识，数据库只存其哈希。所有已认证写操作检查Origin和会话CSRF Token；Axios自动发送，不能仅靠手工构造employee_id越权。退出即时撤销旧会话；刷新不再要求重新登录。sessionStorage仅保存当前用户/角色允许的菜单path与活动path，不保存令牌、员工或工资数据。

## 测试与构建

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
cd ../frontend
npm ci
npm run build
npm audit
# 先启动两个开发服务，安装Chrome；测试会创建明确标记的虚构验收资料
npm run test:e2e
cd ..
backend/.venv/bin/python scripts/verify_persistence.py
backend/.venv/bin/python scripts/verify_static.py
```

Windows把.bin路径替换为`.venv/Scripts/python.exe`。`npm run build`先进行vue-tsc检查再执行Vite。浏览器测试依次运行spec-tabs.mjs、spec-employee-tabs.mjs、spec-business.mjs；只有菜单路径写入存储。测试用例会保留少量虚构业务数据用于验收，不清除旧数据。pytest全部使用隔离临时数据库，包含真实旧六表迁移测试。

运行环境实测：Python3.13.7、Node24.14.0、npm10.9.2；Vue3.5.44、Vite6.4.5、ElementPlus2.14.7、Pinia3.0.3、ECharts6.1.0、Axios1.20.0、TypeScript5.8.3；Python完整依赖见requirements-lock.txt，前端见package-lock.json。

## 数据备份与部署

```bash
cd backend
.venv/bin/python -m app.scripts.backup_db backups/backup.sqlite3
```

备份使用SQLite在线backup API并检查完整性，目标已存在时拒绝覆盖。恢复先复制到独立路径，通过DATABASE_PATH验证；迁移不提供危险的自动降级，需恢复迁移前备份副本。旧库本机备份位于backend/backups/pre-spec-20261027.sqlite3，禁止公开提交。

CloudStudio默认 **Nginx8080 + 构建前端 + 内部FastAPI8000**，脚本为 `bash deploy/start-cloudstudio.sh`；无Nginx时明确选择 `bash deploy/start-fallback.sh` 备用模式。完整步骤见[部署说明](deploy/README-CloudStudio.md)。当前没有实际云端域名或分享权限验收，不能宣称已部署。

## 业务边界与已知限制

请假为整天，默认周一至周五工作，冲突时整笔审批失败；无排班就不自动推断缺勤。工资以整数分存储，历史基本工资为快照，不自动算个税社保或考勤扣款。任务数量完成后方可质检，质检通过后才能确认完成。员工离职禁用账号但保留历史。

登录节流仅单进程内按IP/用户名每分钟10次，重启清空；代理可能共享来源IP，不等于分布式防暴力破解。Cookie安全属性和来源必须在实际HTTPS预览中验证。ElementPlus/ECharts构建仍有大包性能提示；后端测试有第三方弃用警告。当前提供依赖一致性与npm审计结果，未做独立完整安全审计。

原版资料保存在docs/history-20261026，旧CODEx任务书是历史基线；**本次以SPEC.md为准**。最新验收：[checklist.md](checklist.md)、[阶段记录](docs/spec-test-results.md)、[初步审查](docs/review.md)。
