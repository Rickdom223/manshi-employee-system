# 当前需求基线与追踪

最新完整需求为根目录SPEC.md（2026-10-27），本次用户明确要求在原系统上增量开发并实现后台多标签导航。旧任务书和2026-10-26交付属于历史，不再用其无Cookie/无考勤范围限制覆盖新SPEC。

管理员九模块、员工六模块，全部业务走数据库；不公开注册。模块追踪：auth/security对应AUTH；employees对应EMP；dictionaries对应DEP并保留技能；attendance对应ATT；leaves对应LEAVE；payroll对应PAY；tasks对应TASK；exports/reports对应FILE；迁移与verify_persistence对应PERSIST。

前端第3.3节追踪：menus.ts白名单与meta；stores/tabs.ts开关激活恢复；WorkspaceTabs.vue标签栏；TabPane.vue状态/滚动缓存；WorkspaceDialog.vue弹窗保留；dirty.ts未保存确认；auth.js/http.js退出/过期清理；router/index.js同步角色与URL。实际UI-TAB结果见checklist.md。

首装初始化ljm和四部门；升级保留旧账号与历史数据，因此不会为凑四部门而删除原部门。测试/验收资料明确为虚构，不代表真实企业数据或商业上线。
