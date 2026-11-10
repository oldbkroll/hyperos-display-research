# HyperOS 外接显示静态研究

目标：分析工作区 ROM 的多显示器、独立桌面及外接刷新率路径，形成有证据的可逆方案和未来真机验证计划。任务定义见 [docs/maintask.md](docs/maintask.md)。

不连接或操作手机，不修改 ROM/系统镜像，不上传 ROM、APK、反编译代码。公共仓库只保存原创分析、脚本与必要的元数据/哈希。

## 进度与交接

见 [docs/PROGRESS.md](docs/PROGRESS.md) 和 [docs/HANDOFF.md](docs/HANDOFF.md)。各阶段完成后提交、推送；无法完成或缺少证据的部分明确保留。

## 证据标记

- **[ROM]**：本 ROM 静态数据、资源或方法体证据。
- **[AOSP]**：固定版本上游源码，不能替代本 ROM 或真机证明。
- **[推测]**：由证据推导、仍需验证。
- **[待真机]**：本轮未执行。

## 目录

`scripts/` 可复现流程；`analysis/evidence/` 可公开的清单与哈希；`analysis/local/` 本地分析输出；`extracted/` 本地镜像和文件；`tools/` 工具说明与本地隔离安装；`reports/` 研究报告。
