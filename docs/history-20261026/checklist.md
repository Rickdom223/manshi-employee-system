# 验收清单

状态使用：通过 / 未通过 / 待测试 / 无法验证。以下结果均为本机2026-10-26实测，平台结果单独列出。

## 后端自动化

统一命令（backend目录）：`.venv/Scripts/python.exe -m pytest -q --junitxml=../docs/pytest-results.xml`。

| 验收项 | 状态 | 证据与结果 |
| --- | --- | --- |
| 六张表、外键打开、健康检查 | 通过 | test_skeleton.py；2 passed；test_integrity直接插入错误外键抛IntegrityError |
| 拒绝占位密钥、非法路径/过期时间 | 通过 | test_placeholder_rejected、test_security_config |
| 正确凭证登录、me不泄露哈希 | 通过 | test_login_and_me |
| 错密码、停用账号、缺少认证 | 通过 | test_bad_password_disabled_and_missing |
| 过期/篡改/缺失exp/停用用户JWT | 通过 | test_invalid_tokens 4组 |
| 基本登录限速 | 通过 | test_login_rate_limit，第11次429 |
| 员工合法创建持久化、工号重复409 | 通过 | test_create_edit_persist |
| 姓名、电话、日期、无效关联422且不落库 | 通过 | test_invalid_employee 6组 |
| 禁止改工号、编辑后重读 | 通过 | test_create_edit_persist |
| 部门岗位错配、停用新关联拒绝、旧关联保留 | 通过 | test_mismatch_and_disabled_history |
| 字典创建编辑停用、唯一冲突、必填null拒绝 | 通过 | test_dictionary_rules |
| 岗位已被引用不能更换部门 | 通过 | test_mismatch_and_disabled_history |
| 工号/姓名、部门、状态、技能组合查询 | 通过 | test_skills_filters_and_pagination、test_archive |
| 空查询200空数组、分页边界422 | 通过 | test_skills_filters_and_pagination |
| 离职日期约束、重复409、历史仍可查、不删员工 | 通过 | test_archive |
| 一人多技能、重复409、改熟练度、解除不删字典 | 通过 | test_skills_filters_and_pagination |
| 看板随新增/归档变化，空库为0 | 通过 | test_empty_dashboard、test_dashboard_changes |
| 初始化幂等且不覆盖既有密码/员工修改 | 通过 | test_initialize_idempotent；实际init_db重复运行也成功 |
| 所有模块鉴权、统一422/404错误 | 通过 | 各protected测试、test_validation_envelope_and_missing |
| 临时数据库隔离 | 通过 | conftest.py每用例tmp_path独立SQLite，未重置演示库 |
| 全部后端测试 | 通过 | 29 passed，4.06秒；1条第三方弃用警告；pytest-results.xml |
| Python依赖一致性 | 通过 | pip check → No broken requirements found |

## 前端与本地同源代理

| 验收项 | 状态 | 命令/响应与证据 |
| --- | --- | --- |
| lock文件可重装 | 通过 | frontend执行 npm ci；added 87 packages |
| 构建 | 通过 | npm run build → Vite6.4.5成功；Element Plus大包性能提示保留 |
| 依赖审计 | 通过 | npm audit → info/low/moderate/high/critical均0；docs/npm-audit-after.json |
| 3000健康代理 | 通过 | curl -i http://127.0.0.1:3000/health → 200 application/json，data.status=ok |
| 3000未登录业务接口 | 通过 | curl -i http://127.0.0.1:3000/api/employees → 401 application/json，error.code=UNAUTHORIZED |
| 首页与深层路由SPA | 通过 | curl / 和 /employees/1 → 200 text/html |
| 登录、首页真实统计 | 通过 | node tests/e2e.mjs；screenshots/01-login.png、02-dashboard.png |
| 新增→编辑→两技能→熟练度→筛选→归档 | 通过 | Chrome自动化真实UI操作，docs/e2e-results.json；03-employee-skills.png、04-employees.png |
| 部门字典新增编辑停用与岗位入口 | 通过 | e2e“字典页面与新增编辑停用” |
| 岗位、技能页面新增编辑停用 | 通过 | e2e对三个字典逐一新增、编辑及停用，含岗位所属部门选择 |
| 请求均同源、无页面JS错误 | 通过 | e2e所有/api请求origin匹配3000，pageErrors=[] |
| 刷新深层地址回登录，无持久化token | 通过 | e2e检查localStorage/sessionStorage均空、刷新技能页到登录 |
| 退出与404 | 通过 | e2e测试确认退出和未知路由404 |
| 笔记本宽度 | 通过 | Chrome1280×800，document.scrollWidth<=innerWidth |
| Edge完整流程 | 无法验证 | 当前未跑Edge，提供E2E_BROWSER_CHANNEL=msedge切换方法 |

## 配置脚本与数据

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| Windows一键启动 | 通过 | powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1；Vite就绪，3000健康200 |
| Windows端口冲突 | 通过 | 服务已运行时再次执行脚本，WinError10048后明确退出，未换端口/未杀旧服务 |
| Windows退出清理 | 通过 | Ctrl+C后8000连接返回10061（拒绝），脚本自己启动的后端已退出 |
| Bash语法 | 通过 | MSYS GNU Bash5.2.37，sh -n scripts/start_cloudstudio.sh，退出0 |
| Bash缺少Linux虚拟环境预检 | 通过 | sh scripts/start_cloudstudio.sh，退出1并显示建venv和pip安装命令 |
| CloudStudio完整Linux脚本生命周期 | 无法验证 | 当前Windows，无可用WSL/Linux工作空间；需到CloudStudio验证 |
| 在线备份副本完整性 | 通过 | python -m app.scripts.backup_db backups/verified-copy.sqlite3 → integrity_check=ok；备份未加入交付包 |
| 恢复副本两次服务进程重启后数据保留 | 通过 | python scripts/verify_persistence.py → backup_integrity=ok，两次total一致；docs/persistence-results.json |
| .env/数据库/依赖/备份不打包 | 通过 | package_project.py白名单式排除并检查ZIP目录和环境秘密字节，无敏感文件 |

## CloudStudio现场项目

| 验收项 | 状态 | 原因/补验方法 |
| --- | --- | --- |
| preview.yml由平台读取 | 无法验证 | 已生成，仅主入口3000；待实际平台启动 |
| 实际HTTPS 3000预览URL | 无法验证 | 未接入CloudStudio，未编造URL |
| 实际Host允许列表/HMR | 无法验证 | 需平台Network/Console实测 |
| 8000仅自己可见与外部权限 | 无法验证 | 需平台端口面板检查 |
| 外部隐身/非工作空间登录态访问 | 无法验证 | 需真实分享链接与第二窗口 |
| CloudStudio重启保留数据库 | 无法验证 | 本地副本重启通过；云工作空间磁盘/停机需另验 |

修复记录详见 docs/review.md。曾发生测试弹层定位、备份连接未关闭、重启期间连接拒绝等失败；均修复并复验。截图路径均相对docs目录；没有CloudStudio截图。
