# CloudStudio 部署及验收操作

当前默认入口是项目根目录 `sh start.sh`，自动安装依赖、生成配置、备份并升级数据库，再同时启动后端8000与前端3000。平台运行按钮使用同一入口。

完整说明见 [CloudStudio一键启动](CLOUDSTUDIO-ONE-CLICK.md)，当前数据导入见 [迁移当前数据](CLOUD-CURRENT-DATA.md)。

本项目接口前缀为 `/api`，唯一系统管理员为 `admin`；初始化不会恢复已修改的密码。此前8080构建网页的方式保留为手动选择，见 [其他部署方式](../deploy/README-CloudStudio.md)。

本轮仅在本机修改和验证配置，没有向CloudStudio上传、创建或启动应用。实际HTTPS预览链接、平台权限和Linux环境需在云端部署时核对。
