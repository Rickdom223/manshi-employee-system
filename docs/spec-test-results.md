# 三阶段真实测试记录（2026-10-27）

当前环境Windows，Python3.13.7、Node24.14.0、npm10.9.2。未连接CloudStudio。

## 第一阶段

修改：模型增量列/会话/考勤/流水、Alembic迁移与初始化、认证/权限、员工组织兼容扩展、Pinia标签store、菜单/路由、WorkspaceTabs、TabPane、管理员布局与设置。

执行backend目录 `.venv/Scripts/python.exe -m pytest -q`：32 passed；frontend `npm run build`：vue-tsc与Vite成功。浏览器spec-tabs.mjs跑打开/切换/关闭/刷新/历史/dirty。第一次发现KeepAlive未缓存组件，修正后这些检查通过，再进入第二阶段。

## 第二阶段

修改：员工端、请假审批/工作日考勤联动、工资快照与发放、Excel、员工账号开通/重置、六页面、员工标签隔离。

后端全量36 passed；TypeScript+构建成功。spec-employee-tabs.mjs验证管理员退出→员工登录无旧标签、员工三页顶部切换与刷新、会话过期后清理。越权、重复/冲突、金额/工资快照、有效Excel均有pytest覆盖。具备员工权限后进入第三阶段。

## 第三阶段及最终回归

修改：制琴任务及多人关系、质检历史、状态约束、四类统计报表、ECharts、Nginx/静态备用部署、文档、完整业务和迁移用例。

后端最终40 passed，约10秒，一条Starlette/AnyIO弃用警告。pytest-spec-results.xml保存机器可读结果；pip check无损坏依赖。

前端使用实际项目内npm工具执行npm ci、npm run build、npm audit。vue-tsc检查成功；Vite构建成功，保留ElementPlus/ECharts大包性能提示。ECharts5.6的审计问题升级到6.1.0后，npm审计0项，结果npm-audit-spec.json。

浏览器命令 `npm run test:e2e` 包含：spec-tabs.mjs九组、spec-employee-tabs.mjs三组、spec-business.mjs八组。覆盖UI-TAB-01～09及弹窗输入/溢出的额外变体，完整业务链有实际Chrome点击及下载，不用API请求替代所有页面操作。JSON结果与截图存于本目录；errors=[]。

真实完整业务：管理员从页面创建员工并开通账号、录入考勤；员工登录申请请假；管理员审批联动考勤，生成工资、编辑奖金123.45和扣款23.44得到6100.01、标记发放并下载；页面创建5把吉他的多人任务、录入进度、质检通过、确认完成；报表有真实图表及Excel；员工仅能读取本人业务。

修复过的真实问题：KeepAlive的slot缓存方式、账号切换时弹窗Teleport目标未挂载、UTF-8 BOM配置解析，以及测试控件/下拉/弹层定位。最终全部重跑通过；详细原因在review.md。

## 数据与部署检查

- verify_upgrade_data.py：与私有迁移前备份逐表核对，旧管理员1、部门6、岗位3、员工7、技能4、关联11全部保留，foreign_key_check为空；migration-spec.json。
- pytest test_migration.py：独立生成旧六表库并两次Alembic升级，验证主键/密码哈希/备注/技能关系保留。
- verify_persistence.py：独立恢复副本内改密码，两次启动/停止服务进程，第二次沿用会话Cookie，密码及员工/部门/考勤/工资/任务数量不变；persistence-spec.json。原库不被改密。
- verify_static.py：备用静态服务中两种角色深层路由200SPA，未知/api返回404JSON；static-fallback-spec.json。
- Bash语法检查：deploy/start-cloudstudio.sh及start-fallback.sh通过。当前没有Nginx或Linux完整工作空间，不能宣称Nginx -t、Linux生命周期及CloudStudioHTTPS分享权限通过。

所有本机页面业务验收使用明确虚构名称，测试不清空原数据库。旧版e2e.mjs与旧文档是历史资料，当前入口为三个spec测试脚本。
