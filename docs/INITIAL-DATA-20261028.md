# 2026-10-28 初始数据重建

本轮保留V3.0现有设计、业务功能、权限和多标签页，按用户提供的《满氏吉他制琴有限公司_30名员工完整数据_保留职级_新增电话薪资.docx》替换初始数据。此文档的模拟样本是用户本轮明确指定的数据基线，不是之前的自动化测试数据。

## 当前数据库

已实际执行 `scripts/reset_initial_data.py`，从一份全新空库开始建立表结构，先校验完整初始数据，再备份原库并原子替换 `backend/data/manshi.sqlite3`。旧库没有任何一行复制到新库。旧库只存在于独立备份文件内，不参与系统查询。

| 项目 | 重建结果 |
|---|---|
| 系统管理员 | 唯一一个 `admin`，独立于员工 |
| 员工 | 30人，工号严格为字符串1～30，不补零 |
| 在职 / 离职 | 27人 / 3人 |
| 账号 | 31个：1个系统管理员＋30个姓名员工账号 |
| HR | 工号1，李名 |
| 四部门主管 | 汪维 / 杜硕 / 满园 / 高子象，分别绑定制琴生产、质量检验、销售、仓储采购 |
| 部门在职人数 | 制琴生产9、质量检验5、销售7、仓储采购6 |
| 职位与职级组合 | 23个；例如制琴师L2和制琴师L3可同时存在 |
| 电话 | 逐人保存文档中的30个11位模拟号码 |
| 在职月基本工资合计 | 222,900.00元 |
| 离职员工 | 工号9许卓、17唐悠、26冯敏，保留文档离职日期并停用账号 |
| 旧账号 | `demo_admin`、`ljm`及原演示姓名账号均不存在于当前新库 |
| 旧业务 | 原打卡、请假、工资、任务、会话均不复制 |

管理员初始登录为 `admin / Admin123`；在职员工以本人姓名 / `Aa123` 登录，例如 `李名 / Aa123`、`汪维 / Aa123`、`韩涛 / Aa123`。三个离职员工即使使用正确初始密码也无法登录。

文档中的金额是税前月基本工资，保存为员工档案基本工资。HR员工列表、详情、编辑和薪资页可查看，员工只能查看本人；系统管理员及主管部门员工列表不暴露他人金额。三个离职员工的金额保存为离职前基本工资，计算当前在职合计时排除。

文档没有给出特定工资年月、实发工资、打卡、请假或考勤规则，因此不虚构这些记录；按月最终薪资表初始为空，D06未录入月份为0。请假、离职复职与真实月薪录入仍按原V3流程操作。

## 重新执行相同重建

这是一个明确会清空当前业务数据的操作。先停止后端，再从项目根目录执行：

```powershell
& backend/.venv/Scripts/python.exe scripts/reset_initial_data.py
```

Linux：

```bash
backend/.venv/bin/python scripts/reset_initial_data.py
```

脚本流程：校验30人源数据 → 在独立候选文件迁移、确认业务表为空 → 创建唯一admin和四部门 → 单事务导入员工/姓名账号/职位职级/主管/离职事件 → 核验人数、金额、外键和完整性 → 备份当前库 → 原子替换当前库。输入错误、开户失败或候选库校验失败时，旧库保持不动。

备份文件位于 `backend/backups/before-approved-roster-时间-随机标记.sqlite3`。本次实际路径和统计见 `initial-data-reset-results.json`。脚本不提供网页“清库”接口，防止误操作。

## 普通启动与首次安装

日常启动不重建、不覆盖密码或业务。首次空库安装默认导入本轮30人数据；初始化凭据及安装状态会持久化，重复执行初始化保持用户之后的修改。

Windows：

```powershell
# 本机依赖已经安装，可直接运行
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1
```

访问 `http://127.0.0.1:3000`。首次安装命令仍见根目录README。登录HR李名即可维护员工，无需再次初始化HR。

如需独立的空白演示或自动化测试，使用 `INITIAL_DATA_MODE=empty`；该模式只在真正空库建立四部门和admin，不会清除已有数据。`INITIAL_DATA_MODE=roster`为本轮默认值。已有旧数据但未安装本轮初始基线时，初始化会明确拒绝混合，要求使用上述重建脚本。

## 代码与验证

- 规范化源数据：`backend/initial_data/employees_20261028.json`，保存源Word文件名及SHA-256。
- 幂等导入：`backend/app/services/initial_roster.py`；安装标记 `initial_data_state`。
- 新迁移：`backend/alembic/versions/20261028_position_grades.py`，允许同部门同职位名称按职级区分。
- API支持单数字工号、基本工资的录入/编辑/读取；Excel可导入导出职级、电话和基本工资。同名多职级职位必须明确填写职级。
- 页面：保留原布局，补充基本工资字段及 `BaseSalaryReference.vue`，清楚区分档案基本工资和按月最终薪资。
- 新测试：`backend/tests/test_v3_initial_data.py`、`frontend/tests/initial-data-e2e.mjs`。

测试命令：

```powershell
Push-Location backend
& .venv/Scripts/python.exe -m pytest -q --junitxml=../docs/initial-data-pytest-results.xml
Pop-Location
Push-Location frontend
npm run build
Pop-Location
& backend/.venv/Scripts/python.exe scripts/run_v3_e2e.py --approved-roster
& backend/.venv/Scripts/python.exe scripts/run_v3_e2e.py
```

浏览器测试使用独立临时库，不修改本轮重建后的业务库。实际结果分别在 `initial-data-pytest-results.xml`、`initial-data-browser-results.json` 和 `v3-browser-results.json`。

## 最终验收结果

- 后端：41项通过，覆盖逐字段数据核对、唯一管理员、30人开户、三名离职拒绝登录、角色隔离、多职级职位、电话/基本工资、Excel导入导出、重复初始化、备份重建与失败回滚。
- 浏览器：9组本轮初始数据场景通过；原有19组功能回归通过；无页面JavaScript错误。
- 前端TypeScript检查与Vite生产构建通过。
- 更新后的启动入口已通过实际启动与同源代理检查。
- 重建后原业务表均为空；仅新增文档所需的人事/账号/主管/离职事件与初始化审计。

本次旧库备份：`E:\PS work\manshi-employee-system\backend\backups\before-approved-roster-20261028-092206-f711e1.sqlite3`。旧库不参与当前系统查询。
