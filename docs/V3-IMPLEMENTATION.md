# V3.0 代码与接口交付

> 2026-10-28已增加用户确认的30人初始数据、显式备份重建、多职级职位与基本工资，当前数据和新增文件见 [本轮说明](INITIAL-DATA-20261028.md)。

## 当前运行入口

- 前端：`frontend/src/main.js` → `V3App.vue` → `router/v3router.ts`。
- 后端：`backend/app/main.py`，仅挂载认证、V3人事、V3业务和V3看板路由。
- 初始化：`python -m app.scripts.init_db`（Alembic迁移后调用V3幂等初始化）。
- 原两角色路由、制琴任务与旧页面保留在源码中供追溯，当前入口不挂载、不显示，也不提供生产任务接口。

## 修改与新增文件

| 范围 | 主要文件 | 实现 |
|---|---|---|
| 需求 | SPEC.md、docs/history-v1/SPEC.md | V3最新基线、归档V1.1 |
| 模型与迁移 | backend/app/models/__init__.py、backend/alembic/versions/20261027_v3.py | 四角色与账号治理字段、职级、主管、事件、规则、打卡、Decimal薪资；保留旧业务 |
| 认证 | backend/app/core/security.py、core/config.py、routers/auth.py | HttpOnly会话、Origin/CSRF、角色依赖、姓名登录、改密撤销、失败限流 |
| 人事 | backend/app/schemas/v3.py、services/v3.py、routers/v3_people.py | HR引导与恢复、自动开户、同名、职位、员工、Excel、账号/主管/审计 |
| 业务 | backend/app/routers/v3_business.py、services/v3_attendance.py | 打卡、规则版本、月报、请假审批、工资、离职/复职与账号联动 |
| 看板 | backend/app/routers/v3_dashboard.py | 六类真实指标、共享出勤口径、跨月请假、六个月工资 |
| 初始化 | backend/app/scripts/initialize_v3.py、init_data.py | 空库仅四部门与admin，可重复安全执行 |
| 前端布局 | frontend/src/V3App.vue、router/v3menus.ts、router/v3router.ts、stores/tabs.ts | 四角色菜单、路由守卫、内部多标签、缓存隔离与会话失效清理 |
| 前端页面 | frontend/src/views/V3Page.vue、components/V3Business.vue、V3Dashboard.vue、V3Home.vue、EmployeeLifecycle.vue、EmployeeDetails.vue | 全业务表格、筛选、表单、详情、主管配置、离职账号、图表、个人工作台 |
| HTTP与构建 | frontend/src/api/http.js、axios.d.ts、vite.config.js、package.json、package-lock.json | Cookie/CSRF、错误提示、同源代理、TypeScript构建、E2E入口 |
| 后端测试 | backend/tests/test_v3_stage1.py、test_v3_stage2.py、test_v3_stage3.py、test_v3_security.py、test_v3_migration.py、test_v3_concurrency.py、conftest.py、pytest.ini | 31项当前自动化用例、真实临时库与升级测试 |
| 浏览器与部署验证 | frontend/tests/v3-e2e.mjs、run-v3-e2e.mjs、scripts/run_v3_e2e.py、verify_v3_deploy.py | 19组浏览器场景、同源/重启验证，独立库 |
| 升级与交付 | scripts/upgrade_local_v3.py、start_dev.py、process_control.py、package_project.py、deploy/nginx.conf、.vscode/preview.yml、.env.example、backend/.env.example | 自动备份升级核验、源码包、同源配置、环境示例 |
| 文档 | README.md、docs/V3-START.md、V3-ACCEPTANCE.md、V3-IMPLEMENTATION.md、checklist.md、tasks.md | 完整启动、部署、功能复现、验证记录和局限 |

## 主要API

实际可交互文档：服务运行时访问 `/api/docs`；结构定义 `/api/openapi.json`。返回统一 `data`，错误返回 `error.code/message`。列表返回 `total`，分页使用 `page/page_size`。

| 功能 | 端点 | 权限 |
|---|---|---|
| 登录/身份/退出 | POST /api/auth/login、GET /api/auth/me、POST /api/auth/logout | 登录/会话本人 |
| 改密 | POST /api/auth/change-password | 全员本人，旧密码及两次新密码 |
| 初始化状态 | GET /api/bootstrap/status | 仅必要状态 |
| HR引导/恢复 | POST /api/admin/bootstrap-first-hr、POST /api/admin/recover-hr | 系统管理员且无可用HR |
| 固定部门 | GET /api/departments、GET /api/departments/{id}/employees | 所有人查看部门；HR/对应主管查看员工 |
| 职位 | GET/POST /api/positions、GET/PATCH /api/positions/{id} | 登录查看；HR写入 |
| 档案 | GET/POST /api/employees、GET/PATCH /api/employees/{id} | HR管理；本人/主管有限读取 |
| 个人档案 | GET /api/me/employee | 绑定员工本人 |
| Excel | GET /api/employees/import-template、POST /api/employees/import、GET /api/employees/export | HR |
| 离职复职 | POST /api/employees/{id}/leave、POST /api/employees/{id}/rehire | HR，event_date与可选note |
| 账号 | GET /api/admin/users、GET /api/admin/users/{id}、GET /api/admin/departed-users | 系统管理员 |
| 角色/登录名 | PATCH /api/admin/users/{id}/role、PATCH /api/admin/users/{id}/username | 系统管理员 |
| 启停/重置 | POST /api/admin/users/{id}/disable、/enable、/reset-password | 系统管理员，拒绝启用离职账号 |
| 主管关系 | GET /api/admin/departments/supervisors、PUT/DELETE /api/admin/departments/{id}/supervisor | 固定部门信息可读；系统管理员配置 |
| 审计 | GET /api/admin/audit-logs | 系统管理员 |
| 个人打卡 | POST /api/me/punch-in、POST /api/me/punch-out、GET /api/me/attendance?month=YYYY-MM | 绑定员工本人，服务端确定身份和时间 |
| 考勤规则/月报 | GET/POST /api/attendance/rules、GET /api/attendance/monthly?month=YYYY-MM | HR |
| 个人请假 | GET/POST /api/me/leaves、POST /api/me/leaves/{id}/cancel | 绑定员工本人 |
| 主管审批 | GET /api/supervisor/leaves、POST /api/supervisor/leaves/{id}/review | 当前负责该部门的主管，非本人，decision=approve/reject |
| 全员请假 | GET /api/hr/leaves | HR只读 |
| 工资 | GET/POST /api/salaries、PATCH /api/salaries/{id} | HR，amount为十进制最终金额 |
| 本人工资 | GET /api/me/salaries?year=2026 | 绑定员工本人，拒绝替换身份 |
| HR看板 | GET /api/dashboard/hr | HR |
| 健康 | GET /api/health | 服务与数据库连通性 |

不提供部门新增/删除/改名、公开注册、员工账号物理删除或管理员全局薪资读取端点。旧版 `/api/payroll`、生产任务等路由不再挂载。
