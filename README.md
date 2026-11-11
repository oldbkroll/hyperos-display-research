# HyperOS 外接显示静态研究

目标：分析工作区 ROM 的多显示器、独立桌面及外接刷新率路径，形成有证据的可逆方案和未来真机验证计划。任务定义见 [docs/maintask.md](docs/maintask.md)。

不连接或操作手机，不修改 ROM/系统镜像，不上传 ROM、APK、反编译代码。公共仓库只保存原创分析、脚本与必要的元数据/哈希。

## 进度与交接

见 [docs/PROGRESS.md](docs/PROGRESS.md) 和 [docs/HANDOFF.md](docs/HANDOFF.md)。各阶段完成后提交、推送；无法完成或缺少证据的部分明确保留。

后续方向已接受，见 [原生外接桌面接通与兼容性修复计划](docs/NATIVE_EXTERNAL_DESKTOP_PLAN.md)：不依赖第三方桌面，优先复用 MiuiHome 与系统窗口组件；先补齐离线调用链与最小设计，再另行安排设备验证。计划文档已建立，后续阶段尚未执行。

2026-11-10：五个阶段的**本轮初步静态研究**已完成。七个优先分区全部通过 payload manifest 哈希并解包，97 个 packaged Overlay 已扫描，保留 24 组方法证据。设备验证全部 NOT_RUN；没有制作/安装模块，没有修改 ROM 或手机。

| 报告 | 内容 |
|---|---|
| [01 ROM 信息](reports/01-rom-information.md) | 内部版本、58 个分区、七个 EROFS 目标与可续做流程 |
| [02 Android 架构](reports/02-android-display-architecture.md) | 固定 Android 17 源码，区分六项能力 |
| [03 HyperOS 限制](reports/03-hyperos-restrictions.md) | 资格门控、镜像恢复、背屏、SystemUI/Launcher 与原生实现边界 |
| [04 刷新率](reports/04-display-refresh-rate.md) | 条件性 60 渲染投票、下游模式筛选与 HWC/DP 待验证项 |
| [05 实施方案](reports/05-implementation-options.md) | A–E 路线、普通/Root/系统组件权限、可逆性与风险 |
| [06 真机计划](reports/06-device-validation-plan.md) | 只读采集、分级实验、恢复与验收矩阵；本轮未执行 |

目前证据支持优先验证独立次屏 Activity，再评估最小桌面资格配置。已定位的 60 render vote 不等于证明物理输出只能 60 Hz。Launcher 原生次屏入口存在，但具体行为尚未恢复或验证。

复现、证据索引和工具参数见 [analysis/README.md](analysis/README.md)。本地完整性验证：`python scripts/verify_research.py --local --rom`；不带两个选项可只检查公共产物。

## 证据标记

- **[ROM]**：本 ROM 静态数据、资源或方法体证据。
- **[AOSP]**：固定版本上游源码，不能替代本 ROM 或真机证明。
- **[推测]**：由证据推导、仍需验证。
- **[待真机]**：本轮未执行。

## 目录

`scripts/` 可复现流程；`analysis/evidence/` 可公开的清单与哈希；`analysis/local/` 本地分析输出；`extracted/` 本地镜像和文件；`tools/` 工具说明与本地隔离安装；`reports/` 研究报告。
