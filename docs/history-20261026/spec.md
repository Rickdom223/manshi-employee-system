# 功能与接口规格 V1.1 实现版

所有业务 URL 真实包含 `/api`。除 POST /api/auth/login、GET /health 外全部须管理员 Bearer JWT。业务错误、验证错误、404 和500采用统一 error 包装，不回传堆栈。公开 OpenAPI 调试页面已关闭。

## 契约

- 成功：`{"data": {...}}`；创建返回201，读取修改删除关联返回200。
- 分页：`{"data": [], "total": 0, "page": 1, "page_size": 20}`。page>=1，page_size 1–100，超界422。
- 错误：`{"error":{"code":"...","message":"中文提示"}}`。401未认证、403非管理员、404不存在、409唯一/状态冲突、422校验、429登录限流、500通用内部错误。
- 日期 YYYY-MM-DD，枚举 status=active/resigned，proficiency=basic/skilled/expert。未知输入字段拒绝422。

## API 表

| 方法 | URL | 请求与说明 |
| --- | --- | --- |
| POST | /api/auth/login | username、password；data返回access_token、token_type=bearer、expires_in秒 |
| GET | /api/auth/me | id、username、role，无密码哈希 |
| GET | /api/employees | keyword、department_id、status默认active（可resigned/all）、skill_id、page、page_size |
| POST | /api/employees | employee_no、full_name、department_id、position_id、hire_date必填；phone、remark可空 |
| GET | /api/employees/{id} | 全部资料、部门/岗位名称、skills集合 |
| PATCH | /api/employees/{id} | 仅full_name、department_id、position_id、hire_date、phone、remark；部分更新 |
| POST | /api/employees/{id}/archive | resignation_date；active→resigned；重复409 |
| GET | /api/departments | 分页；可is_active筛选 |
| POST | /api/departments | code、name、is_active默认true |
| PATCH | /api/departments/{id} | code、name、is_active部分更新 |
| GET | /api/positions | 分页；可department_id、is_active筛选 |
| POST | /api/positions | code、name、department_id、is_active默认true |
| PATCH | /api/positions/{id} | 同上部分更新，已有员工引用则不可换部门 |
| GET | /api/skills | 分页；可is_active筛选 |
| POST | /api/skills | code、name、is_active默认true |
| PATCH | /api/skills/{id} | 同上部分更新 |
| GET | /api/employees/{id}/skills | 技能名称/编码、字典启用状态、熟练度 |
| POST | /api/employees/{id}/skills | skill_id、proficiency；重复409，停用技能422 |
| PATCH | /api/employees/{id}/skills/{skill_id} | proficiency；仅调整既有关系 |
| DELETE | /api/employees/{id}/skills/{skill_id} | 解除关联，不删除技能字典或员工 |
| GET | /api/dashboard/summary | total、active、resigned、departments、department_distribution |
| GET | /health | SELECT 1检查连接；data.status=ok |

## 业务规则

工号/字典编码为2–20位ASCII英数字、横线或下划线，去首尾空白后唯一；区分大小写。姓名及字典名称去首尾空白，1–50字符。电话可空，非空为5–25位数字、空格、括号、横线，允许前导+。备注最多1000字符。员工列表不返回电话和备注；详情仅管理员可读。

部门/技能的编码和名称分别唯一；岗位编码全局唯一，名称在部门内唯一。空值不得清除必填字段；phone/remark允许null清除。PATCH不接受employee_no、status等字段。岗位和员工部门必须匹配，停用后不能新指派，但可保留员工未修改的历史关联。

归档不删除员工，离职日期不能早于入职日期；归档后修正入职日期不能晚于既有离职日期。一人多技能；解除关联后字典仍存在；停用技能可保留原关联并调整熟练度，但不能新增关联。

看板部门数包含停用部门；部门分布统计所有部门的在职人数（包含零值）。统计采用数据库查询，不硬编码。

用户名/密码校验失败提示相同；停用用户无法登录或使用已有令牌。JWT只接受HS256并要求sub、exp。初始化不覆盖既有密码。退出只清空客户端状态，无撤销表，令牌到期前可能继续有效。
