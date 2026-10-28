# 开发任务与过程

1. [x] 准备：全文读取 V1.1；检查工作区；独立新建工程，不覆盖无关项目。Python 3.13.7、Node 24.14.0；补齐项目内 npm。
2. [x] 后端骨架：配置、六表、稳定 SQLite 路径、外键、异常、健康、隔离库。test_skeleton 2项通过。
3. [x] AUTH-01：Argon2id、JWT、用户状态、限速、认证测试。test_auth 7项通过。
4. [x] ORG/SKL：字典新增编辑停用、关联约束与测试。test_dictionaries 2项通过。
5. [x] EMP：创建修改查询分页归档、技能关联、业务测试。test_employees 11项通过。
6. [x] DASH：统计接口及空数据测试。test_dashboard_init 4项通过。
7. [x] Vue：中文页面、表单、加载/错误/确认、真实 API。Chrome完整流程通过。
8. [x] 同源代理：3000 health/API/SPA 实测。200/401/200，深层地址200。
9. [x] CloudStudio：启动脚本、preview.yml、平台验收说明；Bash语法和缺失环境分支已测试。
   - [ ] CloudStudio实际Linux启停、真实HTTPS预览URL、外部分享/权限：当前无平台环境，无法验证。
10. [x] 收尾：npm ci、构建、29项后端测试、pip check、浏览器流程、npm audit 0、备份副本重启、审查与手册。

阶段执行证据最终记录在 checklist.md 与 docs/test-results.md。

## 阶段文件与运行记录

| 阶段 | 主要文件 | 启动/验证 | 结果与后续 |
| --- | --- | --- | --- |
| 准备 | 原任务书副本、tasks、decision-log、requirements | Python/Node版本检查，定位npm | 原无本项目，隔离新目录；后续建骨架 |
| 骨架 | core/config、database、errors、models、main、tests/conftest | pytest test_skeleton | 2通过；后续认证 |
| AUTH | security、auth、schemas、init_db | pytest test_auth | 7通过；后续字典 |
| ORG/SKL | dictionaries、services/common | pytest test_dictionaries | 2通过；后续员工 |
| EMP | employees路由/服务、员工schema | pytest test_employees | 11通过；后续看板 |
| DASH | dashboard路由 | pytest test_dashboard_init | 4通过；后续Vue |
| Vue/代理 | frontend/src、vite.config、package锁 | npm build、3000 curl、Chrome e2e | 完整路径通过；后续脚本 |
| 部署脚本 | start_cloudstudio.sh、preview.yml、start_windows.ps1 | Bash语法/预检、Windows实际启停 | Windows就绪/端口冲突拒绝/退出清理通过；云端待验 |
| 收尾 | docs、checklist、完整性测试、备份工具 | pytest全量29、npm ci/audit/build、e2e、持久化脚本 | 本地通过，记录限制并打包 |

依赖下载耗时期间继续编写模块，安装完成后按骨架→认证→字典→员工→看板顺序逐套执行测试，再进行整体回归。初选前端版本审计发现7项漏洞，升级后0项，升级后的浏览器与构建已重新验证。
