# HyperOS 外接显示研究

目标：分析工作区 ROM 的多显示器、独立桌面及外接刷新率路径，通过真机验证评估可逆方案。首轮离线任务见 [docs/maintask.md](docs/maintask.md)。

设备实验按授权和阶段准入条件执行。ROM 和系统镜像保持只读。公共仓库只保存原创分析、脚本与必要的元数据和哈希。

## 进度与交接

见 [docs/PROGRESS.md](docs/PROGRESS.md) 和 [docs/HANDOFF.md](docs/HANDOFF.md)。各阶段完成后提交、推送；无法完成或缺少证据的部分明确保留。

2026-11-11 完成首轮无重启真机对照。镜像外屏实测为 2560×1440 @ 60 Hz，系统拒绝向镜像外屏启动普通任务，连接弹窗只提供镜像和取消。临时请求 120 Hz 未通过物理输出验证。结果与恢复记录见 [报告 13](reports/13-device-display-baseline.md)。

后续按 [原生外接桌面计划](docs/NATIVE_EXTERNAL_DESKTOP_PLAN.md) 优先复用 MiuiHome 与系统窗口组件。阶段 2/3 为 `PARTIAL`，尚未选定实现路线。[证据矩阵](reports/07-native-desktop-evidence-matrix.md) · [调用链和职责](reports/08-native-desktop-call-chain.md) · [最小改动条件设计](reports/09-native-desktop-minimal-design.md)

2026-11-10：五个阶段的**本轮初步静态研究**已完成。七个优先分区全部通过 payload manifest 哈希并解包，97 个 packaged Overlay 已扫描，保留 24 组方法证据。设备验证全部 NOT_RUN；没有制作/安装模块，没有修改 ROM 或手机。

| 报告 | 内容 |
|---|---|
| [01 ROM 信息](reports/01-rom-information.md) | 内部版本、58 个分区、七个 EROFS 目标与可续做流程 |
| [02 Android 架构](reports/02-android-display-architecture.md) | 固定 Android 17 源码，区分六项能力 |
| [03 HyperOS 限制](reports/03-hyperos-restrictions.md) | 资格门控、镜像恢复、背屏、SystemUI/Launcher 与原生实现边界 |
| [04 刷新率](reports/04-display-refresh-rate.md) | 条件性 60 渲染投票、下游模式筛选与 HWC/DP 待验证项 |
| [05 实施方案](reports/05-implementation-options.md) | A–E 路线、普通/Root/系统组件权限、可逆性与风险 |
| [06 真机计划](reports/06-device-validation-plan.md) | 只读采集、分级实验、恢复与验收矩阵 |
| [13 真机基线](reports/13-device-display-baseline.md) | 镜像插拔、任务拒绝、实际渲染投票和物理模式对照 |

下一步核对连接入口、桌面资格和外屏任务承载的联动。MiuiHome 次屏入口已在真机解析，仍待验证创建和窗口操作。

复现、证据索引和工具参数见 [analysis/README.md](analysis/README.md)。本地完整性验证：`python scripts/verify_research.py --local --rom`；不带两个选项可只检查公共产物。

## 证据标记

- **[ROM]**：本 ROM 静态数据、资源或方法体证据。
- **真机**：设备日志、运行时配置或现场观察，见报告 13。
- **[AOSP]**：固定版本上游源码，不能替代本 ROM 或真机证明。
- **[推测]**：由证据推导、仍需验证。
- **[待真机]**：本轮未执行。

## 目录

`scripts/` 可复现流程；`analysis/evidence/` 可公开的清单与哈希；`analysis/local/` 本地分析输出；`extracted/` 本地镜像和文件；`tools/` 工具说明与本地隔离安装；`reports/` 研究报告。
