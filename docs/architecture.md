# 当前架构

开发：浏览器→Vite3000→同源/api代理→FastAPI127.0.0.1:8000→SQLAlchemy2/SQLite。

部署默认：浏览器→Nginx8080→Vue构建资源及/api代理→内部FastAPI8000。无Nginx时明确启用APP_SERVE_STATIC备用模式，未知API保持JSON404。

认证：数据库持久会话，Cookie只含随机标识；sessions保存标识哈希、用户、CSRF哈希、到期及撤销时间。来源白名单检查写操作和登录，认证写操作必须带X-CSRF-Token。默认8小时，退出即时撤销；前端刷新调用me，不存认证秘密。

前端：Vue3、兼容保留的JS业务组件、新增TypeScript标签逻辑、Pinia、VueRouter、ElementPlus、Axios、ECharts。菜单注册表定义角色白名单和常驻页；tabs.ts负责开启/恢复/关闭；TabPane对每个标签单独KeepAlive，卸载即释放；WorkspaceDialog管理弹窗活动状态与安全DOM挂载。sessionStorage只存path序列和当前path。

后端：core提供配置/数据库/会话/错误；schemas校验；routers按认证、组织、员工、考勤、请假、工资、制琴任务、报表、员工端分层；services复用编号流水、金额、日期和序列化。保留原技能关系和接口。

数据库15张业务/辅助表，另有Alembic版本表：users、departments、positions、employees、skills、employee_skills、sessions、attendance_records、leave_requests、payroll_records、production_tasks、production_task_members、quality_inspections、audit_logs、number_sequences。编号通过SQLite事务内流水UPSERT生成，非行数+1。金额为整数分，时间戳UTC，自然日与业务统计按北京时间。

迁移可对原六表增量执行，旧主键和哈希保留；新增列有兼容默认值。没有自动破坏性downgrade，回退需恢复独立备份副本。API沿用data分页包装以保留原客户端契约，字段别名明确映射；OpenAPI在/api/docs。
