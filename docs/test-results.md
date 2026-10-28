# 实际运行记录

> 以下为2026-10-26历史记录。当前多标签页版三阶段结果见[spec-test-results.md](spec-test-results.md)。

日期：2026-10-26（Asia/Shanghai）。位置：E:/PS work/manshi-employee-system。当前Windows环境，不是CloudStudio。

## 后端阶段

在backend目录依次执行：

```text
.venv/Scripts/python.exe -m pytest tests/test_skeleton.py -q       2 passed
.venv/Scripts/python.exe -m pytest tests/test_auth.py -q           7 passed
.venv/Scripts/python.exe -m pytest tests/test_dictionaries.py -q   2 passed
.venv/Scripts/python.exe -m pytest tests/test_employees.py -q     11 passed
.venv/Scripts/python.exe -m pytest tests/test_dashboard_init.py -q 4 passed
```

补充test_integrity的外键、错误包装与配置校验3项后，全量执行：

```text
.venv/Scripts/python.exe -m pytest -q --junitxml=../docs/pytest-results.xml
29 passed, 1 warning in 4.06s
.venv/Scripts/python.exe -m pip check
No broken requirements found.
```

警告来自Starlette测试客户端引用AnyIO的弃用别名。测试数据库使用tmp_path隔离；真实演示库未被测试重建或删除。

实际运行setup_env生成随机本机配置，init_db连续执行两次成功。初始化幂等自动测试另验证既有管理员哈希和员工修改不被覆盖。

## 前端阶段

电脑没有系统npm，实际通过 `node ../.tools/package/bin/npm-cli.js` 执行npm命令。下载工具/安装缓存权限问题处理后，依赖安装成功。

```text
npm ci --no-audit --no-fund --cache ../.tools/npm-cache
added 87 packages in 11s
npm run build
Vite 6.4.5，1680 modules transformed，built successfully
npm audit --json
0 vulnerabilities
```

供应商包Element Plus约940kB（压缩前），有超过500kB的构建性能提示；无构建错误。审计前7项（6 high/1 moderate），升级到修复版本后0项；两个审计JSON保存于本目录。

## 3000代理

实际启动FastAPI127.0.0.1:8000与Vite0.0.0.0:3000，执行curl：

| 地址 | 实际响应 |
| --- | --- |
| /health | HTTP200 application/json，data.status=ok |
| /api/employees（无认证） | HTTP401 application/json，error.code=UNAUTHORIZED |
| / | HTTP200 text/html |
| /employees/1 | HTTP200 text/html |

前缀没有rewrite。Chrome请求记录见e2e-results.json，不含密码、请求体、Authorization或响应JWT。

## 浏览器

实际命令：frontend目录 `node tests/e2e.mjs`，使用系统Chrome，Playwright1.64.1，视口1366×900及1280×800。最终10个检查全部PASS：

1. 代理与SPA。
2. 登录与工作看板。
3. 新增员工与部门岗位联动。
4. 编辑员工并读取详情。
5. 分配两项技能、调整熟练度、解除关联并重新分配。
6. 组合技能筛选。
7. 离职归档与状态筛选。
8. 部门、岗位、技能三个字典各自新增编辑停用，含岗位入口与部门联动。
9. 笔记本布局与同源请求；无持久化token、无页面JS错误。
10. 深层路由刷新重新登录、404、退出。

截图：screenshots/01-login.png、02-dashboard.png、03-employee-skills.png、04-employees.png。截图为真实数据库资料，记录全部为自动测试及初始化生成的虚构信息。每次浏览器流程创建独立工号并归档，会留下演示记录，不清理旧库。

## 启动、备份与持久化

Windows一键脚本实际启动成功；服务运行时重启第二份触发端口占用而退出；Ctrl+C后8000连接结果10061，确认自己的后端被清理。

Bash使用MSYS GNU Bash5.2.37语法检查通过；Linux虚拟环境缺失分支正确退出1并给出安装命令。WSL探测提示未安装，没有在Linux环境进行完整启动/信号测试。

`python -m app.scripts.backup_db backups/verified-copy.sqlite3` 完成在线备份与完整性检查。`python scripts/verify_persistence.py` 生成独立临时恢复副本，启动服务、停止、再次启动，两个进程均读到相同人数，完整性为ok。首次运行曾因SQLite连接未显式关闭导致Windows文件清理失败，修复closing后重跑退出0；详情在persistence-results.json。

## 未验证部分

CloudStudio实际部署、HTTPS域名、平台读取preview.yml、外部访问权限、Host/HMR、Linux完整启停及空间重启持久化均未验证。Edge完整自动化未运行。后端未做完整CVE扫描。详见checklist与review。
