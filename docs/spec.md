# 实现接口补充

完整业务和交互规格见根目录SPEC.md；实际OpenAPI见运行中的/api/docs。

沿用原工程响应：普通成功`{"data":...}`，分页`{"data":[],"total":0,"page":1,"page_size":10}`，错误`{"error":{"code":"...","message":"..."}}`。上限100。保留data是增量兼容选择，前后端与测试一致。

旧物理字段employee_no/full_name/resigned保留；API同时输出employee_code/name/left。创建接受新name别名，新员工编号自动生成；不开放修改工号或状态字段，离职须走专用动作。手机号新录入11位，基本工资等金额输出两位小数。

会话为HttpOnly Cookie，不再接受旧Bearer认证。登录/me返回当前用户及CSRF Token，只在JS内存使用；持久会话、退出撤销和改密规则按SPEC。原旧技能接口继续需要管理员会话，未删历史关联。

部署来源、CookieSecure与端口配置见deploy/README-CloudStudio.md；数据库迁移映射与例外见spec-upgrade-decisions.md；完整用例追踪见checklist.md。
