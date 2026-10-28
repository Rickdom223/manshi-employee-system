# CloudStudio 启动方式

## 当前默认：一键开发启动

在项目根目录执行 `sh start.sh`，或点击平台运行按钮。主预览端口为3000，后端8000仅供同源代理访问。脚本自动安装依赖、生成配置、备份和检查已有数据库、启动并检查两个服务。

完整说明见 [一键启动](../docs/CLOUDSTUDIO-ONE-CLICK.md)，当前业务数据迁移见 [迁移说明](../docs/CLOUD-CURRENT-DATA.md)。首次空库初始化管理员为admin和文档30名员工；使用当前数据迁移包则保留导出时的完整数据与账号密码。

## 可选：构建网页后单端口运行

先完成后端依赖、配置和前端构建，再执行 `bash deploy/start-fallback.sh`。FastAPI在8080同时提供网页与API；如选择此方式，将 `.vscode/preview.yml` 的port改为8080、run改为该命令。

## 可选：已有Nginx的环境

完成依赖及配置后执行 `bash deploy/start-cloudstudio.sh`，使用Nginx8080代理后端8000并托管构建资源。需要工作空间预先具备Nginx。本轮未在Linux运行此可选入口。

以上方式选择其一。数据库使用持久化目录，保管backend/.env及备份，HTTPS启用Secure Cookie。实际CloudStudio的HTTPS、外部访问权限与停机行为需要部署后验收。
