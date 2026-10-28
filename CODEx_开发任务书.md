# 满氏制琴有限公司企业员工管理系统｜Codex 开发任务书（CloudStudio 同源代理版）

> **用途**：把本文件放在项目仓库根目录，交给 Codex 阅读并据此生成、运行和验证代码。  
> **版本**：V1.1 · 2026-10-26  
> **项目性质**：AI-Coding 课程实战，1 人独立负责；以虚构数据演示，**不是已上线的商用系统**。  
> **优先级**：先使全部 P0 功能真正可运行，再改善界面；不要添加没有要求的复杂模块。

## 0. 给 Codex 的最高优先级执行指令

你现在是本项目的高级 Python/FastAPI + Vue 全栈开发工程师、测试工程师及技术文档维护者。**请在当前工作区直接实现可运行项目，而不是只回复代码片段或实施建议。**

1. 先检查当前目录，若已有代码/文档先读取，不可随意覆盖；优先阅读本文件及可获得的《满氏制琴有限公司企业员工管理系统项目介绍与功能规格说明书（Spec）V1.0》。
2. **本文件作为 V1.1 技术实施补充**：凡涉及 CloudStudio 开发/预览的访问架构，采用「**浏览器仅访问 Vue/Vite 3000 端口 → Vite 对 `/api` 反向代理到 FastAPI `127.0.0.1:8000`**」，替代 V1.0 中「演示时必须由 FastAPI 8000 端口托管前端」的默认描述。其他 P0 业务规则以 V1.0 Spec 为基准。若无法获取原始 Word 文档，本文件已列出实现所需的核心要求，可据此开发。
3. **这次不引入 Cookie 登录或刷新令牌**；仍采用 JWT + HTTP Bearer，前端只在内存保存 access token，刷新页面需要重新登录。采用同源代理是为以后支持 HttpOnly Cookie 做准备，**不是现在就实现 Cookie**。
4. 按阶段完成：检查环境 → 建目录 → 后端与数据库 → 登录认证 → 员工/部门/岗位/技能 → 看板 → Vue 界面 → CloudStudio 脚本/预览 → 测试/文档。每阶段先检查、再写代码、运行测试、修复错误，避免一次性生成后未经验证就宣称完成。
5. 允许为实现必需功能补充少量合理细节；如与本 Spec 冲突，先在 `docs/decision-log.md` 记录选择理由，不能悄悄修改要求。非必要时不要要求用户临时选择技术栈。
6. 严禁硬编码真实密码、JWT 签名密钥和真实员工信息；不得对外发布数据库文件、`.env`、密钥或调试信息。示例数据一律虚构。
7. 输出完整工程及文档：README、依赖/锁文件、`.env.example`、启动脚本、`.vscode/preview.yml`、测试、`tasks.md`、`checklist.md`、初步审查报告及操作手册。最终汇报**实际执行过的命令和测试结果**；不能运行的部分明确标注“未验证”，不得伪称部署成功。

## 1. 项目目标与边界

- 名称：**满氏制琴有限公司企业员工管理系统**。
- 用户：第一版只有**管理员**；车间主管、普通员工、自助打卡不在 P0。
- 场景：面向吉他制造企业，集中管理员工档案、部门岗位和制琴工艺技能，提供人员概况统计。
- 特色：员工有一个主要岗位，但可关联**多项制琴技能**，支持按技能找人。
- 原则：简单、真实可用、逻辑清楚、便于答辩。不可把它做成 MES、ERP、工资系统或复杂工作流。
- 真实性：企业部门、工序和人员规模尚未实地核实；数据仅是课程演示样例，不应宣称已投入满氏制琴实际使用。

### 1.1 P0 必做功能（全部实现）

| ID | 模块 | 最低要求 |
| --- | --- | --- |
| AUTH-01 | 管理员登录/退出 | 用户名+密码；安全哈希；JWT；未登录接口 401；登录退出可用 |
| EMP-01 | 新增员工 | 工号唯一；姓名、部门、岗位、入职日期必填；后端严格校验 |
| EMP-02 | 员工查询 | 列表、分页、工号/姓名关键词、部门、状态、技能组合筛选 |
| EMP-03 | 修改员工 | 允许更新姓名、部门、岗位、联系电话、入职日期、备注；工号创建后固定 |
| EMP-04 | 离职归档 | `active → resigned`，记录离职日期；不物理删除员工记录 |
| ORG-01 | 部门管理 | 新增、编辑、启用/停用，编码/名称唯一 |
| ORG-02 | 岗位管理 | 新增、编辑、启用/停用，岗位属于部门；不能跨部门选错岗位 |
| SKL-01 | 技能字典 | 新增、编辑、启用/停用；技能编码与名称唯一 |
| SKL-02 | 员工技能 | 一人多技能；熟练度；添加、调整、解除关联；按技能筛选 |
| DASH-01 | 首页统计 | 员工总数、在职、离职、部门数量、在职员工部门分布（真实数据库计算） |

### 1.2 P1 非本次必做（先不实现）

考勤/请假、薪资核算、计件工资、制琴生产订单、库存、复杂审批、多角色细粒度权限、微信登录、邮件短信、Refresh Token、Cookie 登录、AI 排班。不能为了“企业级”而擅自扩展这些模块。

## 2. 固定技术选型

| 层 | 选型 | 约束 |
| --- | --- | --- |
| 前端 | Vue 3 + Vite + Vue Router + Element Plus + Axios | 中文界面；简洁、可用；不要再并列引入 React |
| 后端 | Python 3.11+（以 CloudStudio 实际支持版本为准）+ FastAPI + Pydantic | JSON REST API，按层组织 |
| 持久层 | SQLAlchemy 2.x + SQLite | SQLite 打开外键约束；数据库文件位置稳定且可备份 |
| 认证 | PyJWT + `pwdlib[argon2]` | HS256 JWT；Argon2 密码哈希；令牌只存浏览器运行内存 |
| 后端测试 | pytest + FastAPI TestClient | 独立测试数据库，避免污染演示数据 |
| 前端构建 | npm + Vite | 提交 `package-lock.json`，固定可以工作的版本 |
| 云端 | 腾讯云 CloudStudio | 唯一对外入口为 3000 端口预览链接，8000 仅供内部代理 |

若环境存在版本兼容问题，采用兼容、稳定的版本并记录实际使用版本，不要猜测依赖 API。首版不强制 Docker、Redis、Nginx、Celery、消息队列或微服务。

## 3. 重要架构：CloudStudio 同源代理（必须按此实现）

```text
浏览器（只打开一个 HTTPS 预览地址）
https://<实际 CloudStudio 3000 端口预览域名>/
      │
      ├── GET /、/employees、/skills ...  → Vue/Vite SPA（工作空间 0.0.0.0:3000）
      │
      ├── /api/* ── Vite server.proxy ──→ FastAPI（工作空间 127.0.0.1:8000）
      │                                      └── SQLAlchemy → SQLite
      │
      └── /health ── Vite server.proxy ─→ FastAPI /health
```

**必须满足**：

1. 浏览器中的 API 请求使用 `/api/...` **相对路径**，而非 `http://localhost:8000`，更不能使用单独的 CloudStudio 8000 外网链接。浏览器中的 `localhost` 指用户自己的电脑，不是 CloudStudio 容器。
2. Vite 监听 `0.0.0.0:3000`，后端优先监听 `127.0.0.1:8000`；Vite 的代理 target 是内部的 `http://127.0.0.1:8000`。
3. FastAPI 所有业务路由必须真实带 `/api` 前缀：**Vite 的代理不改写或删除 `/api`**。
4. `/health` 也代理到 FastAPI，使浏览器在唯一的 3000 预览地址上检查后端健康。
5. 前端路由刷新可回到 SPA，不可因为深层页面 `/employees/1` 刷新而 404。
6. 此处“同源”指**浏览器看到的页面与 API 都由 3000 的同一个 origin 提供**，不是仅仅给 FastAPI 配置 `allow_origins=['*']`。
7. 同源模式下不应依赖宽松的 CORS 配置；如需在本地分别直连调试，严格限定本地 origin，不允许生产/预览环境开放 `*` + credentials。
8. 3000 端口的 Vite 开发服务器只作为课程临时演示与调试入口，不应当成长期生产服务器；不能在公开预览里使用真实员工数据。CloudStudio 工作空间停机或链接权限变化会影响可访问性。

### 3.1 必须实现的 `frontend/vite.config.js`（可等价改为 TS）

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 不能 rewrite 删除 /api，后端路由本来就带 /api。
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- 不要直接设置 `server.allowedHosts: true`。如 CloudStudio 提示 `Blocked request`，先检查实际预览 Host 与平台设置；必要时使用 Vite 官方支持的 `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS` 环境变量，**仅添加准确的预览主机名**，不要使用所有域名通配。
- 如果预览 WebSocket/HMR 出现问题，先查 Network/Console 和 CloudStudio 端口预览规则，再作最小修改；不准为绕过错误关闭整体主机安全校验。

### 3.2 前端 API 客户端（必须）

```javascript
// src/api/http.js 的设计要点：
// ① baseURL 使用 '/api'，请求如 http.get('/employees')。
// ② token 仅存 JS 运行内存（内存变量或非持久 Pinia state）。
// ③ 有 token 时加 Authorization: Bearer <token>。
// ④ 401 清理登录态并跳转 /login。
// ⑤ 后端错误信息用于提示，但不能展示内部堆栈。
// ⑥ 不使用 localStorage/sessionStorage 保存 token。
```

建议使用 Axios 拦截器；前端的 `api` 客户端与路由守卫应共用一份认证状态。页面刷新时登录状态清零并进入登录页是本版本**预期行为**，不要误判为 CloudStudio 代理故障。

### 3.3 CloudStudio 一键启动方式（必须实际生成和测试）

提供 `scripts/start_cloudstudio.sh`（Linux bash），行为如下：

- 在仓库根目录定位 backend/frontend，不依赖从哪个目录调用。
- 检查 `backend/.venv`、Node/npm、必需的 JWT 密钥配置；不满足时友好退出并显示对应安装命令。
- 使用虚拟环境 Python 启动 `uvicorn app.main:app --host 127.0.0.1 --port 8000`，将进程作为后台子进程。
- 前台启动 `npm run dev -- --host 0.0.0.0 --port 3000`，端口被占用时直接报错，不悄悄换端口。
- 用 `trap` 确保脚本结束时关闭自己启动的后端进程；不误杀其他人的进程。
- 启动前检查/创建 `backend/data`（不得在每次启动时删除旧数据库）；建表与初始化通过单独可重复执行的脚本进行。
- CloudStudio 环境中自动取得的预览 URL 必须由平台实际返回或从平台环境变量生成，**不要硬编码任意工作空间 ID**。

`.vscode/preview.yml` 建议内容（根据 CloudStudio 实际环境做兼容调整）：

```yaml
apps:
  - port: 3000
    run: bash scripts/start_cloudstudio.sh
    root: .
    name: 满氏制琴员工管理系统
    mainPort: true
```

注意：`preview.yml` 的 `port:` 不得省略；**仅配置 3000 为主要公开入口**。不应主动提供 8000 的公开预览地址。若 CloudStudio 自动发现 8000，设置为“仅自己可见”，同时确保各业务 API 总是要求认证。`0.0.0.0` 是前端监听地址，后端的内网监听按这里的 `127.0.0.1` 实施。

### 3.4 本地调试指令（README 要写出实际版本）

以下是预期用法，Codex 应按生成的工程路径核对后写入 README，且实际执行：

```bash
# 终端 A：首次安装依赖与启动后端（在仓库根目录）
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 复制 .env.example 到 .env，再设置安全的 JWT_SECRET_KEY；不可提交 .env
.venv/bin/python -m app.scripts.init_db
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 B：安装前端并启动（在仓库根目录）
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 3000

# 后端/代理验证：
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:3000/health
curl -i http://127.0.0.1:3000/api/employees  # 未登录应为 401
```

> `python -m app.scripts.init_db` 是预定路径。Codex 创建的初始化脚本必须与 README 中命令一致；不允许文档写了命令却没有实现文件。Windows 开发可在 README 中提供对应的 PowerShell 命令，CloudStudio 主环境为 Linux。

## 4. 登录认证与安全细节（P0）

- `POST /api/auth/login` 接受 `{ "username": "...", "password": "..." }` JSON；合法凭证返回访问令牌、`token_type: "bearer"`、`expires_in`，必要时通过统一 `data` 包装（见第 7 节）。
- 使用数据库 `users.password_hash` 保存 Argon2id 哈希；不得存明文或自制 MD5/SHA256 密码哈希。
- JWT 使用 HS256 和**运行环境提供的高强度随机密钥**（如 `JWT_SECRET_KEY`），声明至少包含 `sub`、`exp`，并检查签名、过期、算法及对应用户的启用状态；默认访问令牌有效期建议 30 分钟，可配置。
- FastAPI 统一依赖进行 `Authorization: Bearer ...` 校验。`GET /api/auth/me`、全部员工/部门/岗位/技能/统计接口必须鉴权；只有登录、健康检查与必要静态资源匿名可访问。
- 登录失败回复统一且不泄露是账号还是密码错误。要有基本限速/节流保护；若环境不便实现可靠的服务端限速，明确在 README 中列出公开演示的限制与风险，不得虚称已防暴力破解。
- Vue 路由未登录统一进入 `/login`；登录成功进入首页；退出清除内存 Token；刷新后须重新登录。
- **注意：前端退出不等于 JWT 服务器端立即撤销**。本版没有服务端 JWT 撤销表，请在操作手册如实说明；不得将“页面退出”写成“旧 Token 立刻作废”。
- 不使用 Cookie 保存令牌，不实现 HttpOnly 刷新机制；但 API 相对路径的同源设计为下一版 Cookie 留好条件。下一版若引入 Cookie，必须再补 CSRF 防护、Cookie 属性、服务端撤销/轮换及测试，不可直接沿用目前的退出语义。

## 5. 数据库设计（6 张核心表，禁止擅自新增考勤表）

数据库文件建议放在 `backend/data/manshi.sqlite3`，使用**基于文件位置计算的绝对路径**，避免从不同工作目录运行造成“数据丢失”。路径可通过受控环境变量覆盖，测试使用独立临时 SQLite 数据库；启用 `PRAGMA foreign_keys=ON`。

| 表 | 字段（按需增加必要索引/时间戳，但不得改变含义） |
| --- | --- |
| `users` | `id` PK；`username` UNIQUE NOT NULL；`password_hash`；`role='admin'`；`is_active`；`created_at` |
| `departments` | `id` PK；`code` UNIQUE；`name` UNIQUE；`is_active`；`created_at` |
| `positions` | `id` PK；`code` UNIQUE；`name`；`department_id` FK；`is_active`；联合 UNIQUE(`department_id`,`name`) |
| `employees` | `id` PK；`employee_no` UNIQUE；`full_name`；`phone` NULL；`department_id` FK；`position_id` FK；`hire_date`；`status`；`resignation_date` NULL；`remark` NULL；`created_at`；`updated_at` |
| `skills` | `id` PK；`code` UNIQUE；`name` UNIQUE；`is_active` |
| `employee_skills` | `id` PK；`employee_id` FK；`skill_id` FK；`proficiency`；`updated_at`；联合 UNIQUE(`employee_id`,`skill_id`) |

枚举取值：`employees.status ∈ {active, resigned}`；`employee_skills.proficiency ∈ {basic, skilled, expert}`；`users.role=admin`；各字典 `is_active` 为布尔值。

**强制业务约束**：

1. 工号建议 2–20 位英数字、`-`、`_`；去空格后唯一；用户名不能与密码相同；账号敏感字段不返回给前端。
2. 姓名 1–50 字，去除首尾空白，空字符串非法；电话可选，非空做长度与格式合理性验证。
3. 员工的 `position.department_id` **必须等于** `employee.department_id`，后端新增/编辑时核验；停用部门或岗位不得关联到新员工或新的岗位调整。
4. 已被引用的部门/岗位/技能通过停用管理，不物理删除历史；调整既有记录时允许保留未修改的历史关联，但不允许新指派到停用字典。
5. 员工归档只改变 `status` 并写入 `resignation_date`，日期不能早于 `hire_date`；重复归档返回 409；归档员工仍可在状态筛选中找到。
6. 一员工多技能，重复关联拒绝为 409；熟练度只能 `basic/skilled/expert`；移除关联只删除 `employee_skills` 的对应行，不删除员工/技能。
7. 唯一约束、外键和业务规则由后端保证；不能仅靠 Vue 表单校验。
8. 初始化脚本应**幂等**：重复执行不重复造数据、不覆盖已有管理员密码和员工信息；使用虚构名称，不要生成看似真实的个人手机号。

## 6. 前端界面与交互（要求能现场演示）

采用简洁、正式的中文企业管理后台风格。示例首页抬头可写“满氏制琴｜员工管理平台”，**不要擅自使用未经授权的实际企业 logo 或照片**。

- `/login`：用户名、密码、校验提示、登录等待状态；错误密码显示通用错误。
- `/`：首页看板，总人数、在职、离职、部门数、部门人数柱状图；无数据时零值与空状态。
- `/employees`：员工列表，姓名/工号搜索、部门/状态/技能筛选、分页、新增、编辑、归档。
- `/employees/:id`：员工详情，展示岗位、部门、技能、熟练度、归档信息；从列表可进入。
- `/departments`：部门列表与表单；可进行启用/停用；岗位关联入口。
- `/positions`：岗位列表与表单，按部门筛选；编辑员工时部门与岗位联动。
- `/skills`：技能字典维护；员工详情或编辑弹窗中可分配/调整/移除技能。
- 全局左侧导航、顶部账号与退出、404 页；提供请求加载状态、无数据状态、错误提示、操作二次确认；中文用户提示易懂。
- 不要只做静态假数据表格。前端所有核心增删改查（员工归档为软删除）**必须连真实 API 和 SQLite**。
- 不在员工列表展示多余敏感信息；手机号码可在列表中遮罩（详情按管理员权限展示）。
- 为降低复杂度，不要求自适应 App，但至少桌面 Chrome/Edge 正常使用，常见笔记本宽度不溢出。

## 7. REST API 固定清单与响应契约

统一 `prefix = /api`，日期 JSON 为 `YYYY-MM-DD`；时间字段统一 ISO 8601（建议 UTC 存储）；列表分页默认 20 条，`1 ≤ page_size ≤ 100`。

| 方法 | URL | 描述 |
| --- | --- | --- |
| POST | `/api/auth/login` | 登录（匿名） |
| GET | `/api/auth/me` | 当前管理员 |
| GET | `/api/employees` | 分页筛选员工：`keyword`、`department_id`、`status`、`skill_id`、`page`、`page_size` |
| POST | `/api/employees` | 新增员工 |
| GET | `/api/employees/{id}` | 员工详情 |
| PATCH | `/api/employees/{id}` | 编辑员工，不允许修改工号 |
| POST | `/api/employees/{id}/archive` | `{"resignation_date":"YYYY-MM-DD"}` 离职归档 |
| GET / POST | `/api/departments` | 部门查询/新增 |
| PATCH | `/api/departments/{id}` | 部门修改/停用 |
| GET / POST | `/api/positions` | 岗位查询/新增 |
| PATCH | `/api/positions/{id}` | 岗位修改/停用 |
| GET / POST | `/api/skills` | 技能查询/新增 |
| PATCH | `/api/skills/{id}` | 技能修改/停用 |
| GET | `/api/employees/{id}/skills` | 员工技能查询 |
| POST | `/api/employees/{id}/skills` | 新增技能关联；重复返回 409 |
| PATCH | `/api/employees/{id}/skills/{skill_id}` | 调整熟练度（是对此前 Spec 的最小必要细化） |
| DELETE | `/api/employees/{id}/skills/{skill_id}` | 解除关联 |
| GET | `/api/dashboard/summary` | 统计总数和按部门人数 |
| GET | `/health` | 健康检查，无 `/api` 前缀 |

**统一格式**：

普通成功响应示例：

```json
{"data":{"id":1,"employee_no":"MS0001","full_name":"演示员工甲","status":"active"}}
```

分页响应示例：

```json
{"data":[{"id":1,"employee_no":"MS0001","full_name":"演示员工甲"}],"total":1,"page":1,"page_size":20}
```

业务错误响应示例：

```json
{"error":{"code":"EMPLOYEE_NO_EXISTS","message":"工号已存在"}}
```

HTTP 状态：200 查询/修改；201 创建；400 业务失败；401 未认证；403 无权限；404 不存在；409 冲突；422 校验失败；500 服务器错误（不得返回内部敏感堆栈）。对于 FastAPI 默认验证异常请定义统一异常处理器，保证前端能按约定解析业务错误。返回对象不能包含密码哈希或令牌签名密钥。

**接口补充细节**：

- `POST /api/employees` 请求示例：

```json
{"employee_no":"MS0001","full_name":"演示员工甲","department_id":1,"position_id":2,"hire_date":"2026-10-01","phone":null,"remark":"课程演示数据"}
```

- `POST /api/auth/login` 请求 JSON：`{"username":"demo_admin","password":"<通过环境变量设置的演示密码>"}`，成功以统一格式返回 `access_token`、`token_type: "bearer"`、`expires_in`。
- 不能因为登录后访问 `/api` 返回 404 而在代理中使用 `rewrite: path => path.replace(/^\/api/, '')`。**本文件的 FastAPI 真实路由就叫 `/api/employees`。**
- 员工列表 `status` 默认 `active`；显式传 `resigned` 查看离职，传 `all` 可看全部。若实现不同参数命名，前后端和文档必须完全同步，且不能破坏验收行为。
- 统计从数据库计算，不允许写死。

## 8. 目录、配置与脚本交付要求

Codex 建议创建如下结构，必要时按工程习惯略作调整，但运行命令必须准确：

```text
manshi-employee-system/
├── CODEx_开发任务书.md           # 本文件，可拷贝或保留原名
├── README.md
├── .gitignore
├── .vscode/
│   └── preview.yml
├── scripts/
│   └── start_cloudstudio.sh
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── api/
│       ├── router/
│       ├── stores/                 # 或其他非持久化认证状态方案
│       ├── views/
│       └── components/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── data/                    # 放数据库（排除 git）
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # 配置、JWT、数据库
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── scripts/init_db.py
│   └── tests/
├── docs/
│   ├── requirements.md
│   ├── spec.md
│   ├── architecture.md
│   ├── decision-log.md
│   ├── review.md
│   ├── cloudstudio-deploy.md
│   └── user-manual.md
├── tasks.md
└── checklist.md
```

- `.env.example` **只放变量名和安全占位提示**，例如 `JWT_SECRET_KEY=REPLACE_WITH_RANDOM_SECRET`、`ACCESS_TOKEN_EXPIRE_MINUTES=30`、`INITIAL_ADMIN_USERNAME=demo_admin`、`INITIAL_ADMIN_PASSWORD=REPLACE_BEFORE_INIT`。启动时检测并拒绝默认占位密钥，避免公开演示被接管。
- `.gitignore` 至少排除：`.env`、`.venv/`、`node_modules/`、`dist/`、`__pycache__/`、`.pytest_cache/`、`*.sqlite3`、`*.db`、日志以及本地备份。
- `init_db` 初始化管理员和少量虚构部门、岗位、技能、员工。示例数据使用“演示员工甲”等明显非真人字段。
- `README.md` 说明安装、环境变量、数据库初始化、两个进程启动、CloudStudio 单入口启动、测试及故障排除。运行顺序不能依赖不存在的命令。
- `docs/cloudstudio-deploy.md` 附部署说明：选择 CloudStudio Python+Node 工作空间、安装依赖、设置环境变量、执行数据库初始化、按 `preview.yml` 启动、预览 3000 端口、外部浏览器测通 API/页面、记录截图与实际 URL。停止空间会影响远程访问；不能宣称永久在线。

## 9. 必须完成的测试与现场验收

### 9.1 后端自动化（pytest）

- 认证：正确账号密码登录成功；错误密码拒绝；未登录访问 `/api/employees` 为 401；过期/篡改 JWT 拒绝；停用账号拒绝。
- 员工：合法新增持久化；工号重复 409；空姓名 422；无效/停用部门岗位或错配 422；编辑后重读正确；非法日期不落库。
- 列表：工号/姓名、部门、状态、技能联合筛选；分页边界；空结果返回 200 + 空列表。
- 归档：在职统计减少；离职仍可查；日期不早于入职；重复归档 409；不物理删除。
- 部门岗位：新建和停用成功；停用后不能进行新的关联；旧员工记录保留。
- 技能：一员工多技能；重复关联 409；修改熟练度正确；解除关联不删除技能字典。
- 看板：数据库人数变化引起正确统计变化，空数据库为 0 而不是 500。
- 数据库：启用外键；测试使用临时隔离库；避免删除 CloudStudio 演示数据。

### 9.2 同源代理与 CloudStudio（关键验收）

在工作空间或本地启动两个服务后，**在 3000 端口验证**：

```bash
curl -i http://127.0.0.1:3000/health
# 预期：200 + 后端健康 JSON，证明转发到 8000

curl -i http://127.0.0.1:3000/api/employees
# 预期：401 JSON，而不是 Vite 的 index.html / 404，证明 /api 代理正确

curl -i http://127.0.0.1:3000/
# 预期：200 HTML，证明前端可访问
```

还需浏览器实际检查：

1. 打开 CloudStudio **3000 的单一预览链接**；Vue 登录页加载，无 `Blocked request`。
2. 以演示账号登录；浏览器 Network 面板可看到发往**当前域名**的 `/api/auth/login` 和 `/api/employees`，没有跨域/CORS 报错。
3. 新增员工 → 编辑 → 赋予两项技能 → 技能筛选 → 归档 → 查看首页统计，整条路径可演示。
4. 刷新页面重新登录（当前版本的预期行为），旧会话不会被持久化到 localStorage。
5. 访问 `/employees`、`/skills` 等前端深层路由并刷新时不出现 404。
6. 只开放对外展示必要的 3000 入口，严格检查 8000 预览端口访问权限。
7. 重启后员工数据仍存在；另行执行数据库备份/恢复副本测试。
8. 再使用一个非工作空间登录态的浏览器窗口或隐身窗口打开**真实外部分享链接**测试；记录是否因 CloudStudio 可见性配置而需要登录。注意公开访问的演示账号必须用非真实数据。

### 9.3 验收清单与证据

必须生成 `checklist.md`：对每个验收项记录 `待测试 / 通过 / 未通过 / 无法验证`，包含执行命令、实际响应、截图路径和修复记录。运行失败时如实记录，不能凭“代码看起来正确”勾选通过。

## 10. Codex 分阶段工作顺序（按顺序执行）

1. **准备**：检查 Node、npm、Python 版本，阅读已存在文件，生成/更新 `tasks.md`，列出 P0 顺序与依赖；复述设计冲突与已做决定。
2. **后端骨架**：配置读取、数据库连接、模型、初始化、统一异常、`/health`、测试数据库。
3. **AUTH-01**：账户初始化、Argon2id 哈希、JWT、认证依赖、登录和 `/me`，完成认证测试。
4. **ORG 与技能字典**：部门、岗位、技能 CRUD（停用代替删除），写关联约束测试。
5. **EMP**：员工 CRUD、分页搜索、离职归档；员工技能绑定与熟练度管理；运行所有业务测试。
6. **DASH**：统计接口及空数据测试。
7. **Vue**：Router、Element Plus 布局、登录、员工/部门/岗位/技能、看板页面，确保全部走真实 API。
8. **同源代理**：`vite.config.js` `/api` 与 `/health` 代理，检查 3000 端口 curl 以及页面 Network。
9. **CloudStudio**：脚本和 `.vscode/preview.yml`，记录真实预览步骤；平台不在当前环境时，标注“需到 CloudStudio 验证”，不要编造 URL。
10. **收尾**：`npm run build`、`pytest`、必要代码检查、README、Spec 追踪、审查报告、操作手册、`checklist.md`；汇总实际文件与操作步骤。

**工作输出约定**：每一阶段给出「本阶段改了哪些文件、如何启动、实际跑了哪些测试、结果是什么、下一阶段做什么」。若你有直接执行工具，就运行代码并修复错误；不允许仅输出大段伪代码冒充完成。

## 11. 提交成果与课程对应关系

| 课程提交项 | 此工程负责提供 |
| --- | --- |
| 1 项目介绍文档 | `docs/requirements.md` 与已有项目介绍 Word（可按需整理） |
| 2 功能规格说明书（Spec） | `docs/spec.md`、`docs/architecture.md`、数据库与接口说明、`docs/review.md` |
| 3 汇报 PPT | 后续根据真实代码、截图、测试与单人任务分工制作（本阶段不要编造 PPT 成果） |
| 4 完整代码 | `frontend/`、`backend/`、启动脚本、依赖、配置示例、必要测试 |
| 5 操作手册 | `docs/user-manual.md`，含登录、员工、部门、岗位、技能、统计、退出和错误处理 |
| 过程证据 | `tasks.md`、`checklist.md`、AI 提示词与迭代记录、实际 CloudStudio 访问地址和截图 |

## 12. 云平台与安全注意（必须遵守）

- CloudStudio 是课程部署和外部演示环境，不保证预览 URL 永久有效，也不等于长期生产服务。
- Vite 开发服务器的公开预览面向课堂临时调试，**不可上传真实员工个人信息**。如果要投入真实企业使用，需改为构建后的静态前端 + 经配置的生产级同源代理、HTTPS、会话撤销、访问审计和备份机制。
- 本版不要向前端暴露管理密钥，不要打印 JWT、密码和数据库完整敏感字段到日志。没有设置安全环境变量时拒绝启动管理员登录初始化。
- CloudStudio 端口设置里如果有“公开 / 仅自己可见”，演示前按教师访问需求明确选择，并检查后端入口权限；切勿以“未提供 URL”作为保护机制。
- 未来改用 Cookie 时，可能涉及 CloudStudio 预览网关的 Cookie 属性与站点作用域问题，必须在实际预览 URL 中测试 `Set-Cookie`、`SameSite`、`HttpOnly`、`Secure`、`Path`、注销撤销及 CSRF；**不属于当前版本的开发任务**。

## 13. 资料来源与说明（供 Codex 校核，不要求联网才能执行）

- 《满氏制琴有限公司企业员工管理系统项目介绍与功能规格说明书（Spec）V1.0》，2026-10-26：项目既有的业务规则和接口设计。**本 V1.1 文件只明确调整 CloudStudio 同源代理方案和少量必要接口细化**。
- 官方 CloudStudio 端口及 Web 预览：https://cloudstudio.net/docs/guide/code_editing/productivity_plugin/port-plug/
- 官方 CloudStudio `preview.yml`：https://cloudstudio.net/docs/guide/code_editing/basic_operations/how-to-run/
- 官方 CloudStudio URL 与监听地址：https://cloudstudio.net/docs/guide/code_editing/FAQ/url-configuration/
- 官方 Vite `server.proxy` 与 `allowedHosts`：https://vite.dev/config/server-options
- 官方 FastAPI JWT 与密码哈希：https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

---

**Codex 现在开始执行**：先输出简明的工程检查结果和开发任务清单，然后**直接在工作区分阶段创建完整代码与文档并运行可执行的测试**。优先保证 P0 全部跑通、单一 CloudStudio 3000 预览地址可访问、前后端同源 API 调用正确；最后给出实际运行结果和未验证项。不要把讨论性的回答当成项目交付。
