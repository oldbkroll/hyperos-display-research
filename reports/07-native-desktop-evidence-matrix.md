# 07 原生外接桌面：证据矩阵

2026-11-11，原生计划阶段 1。基线 `a1cab8a`：popsicle / `OS4.0.6.0.XPBCNXM` / Android 17。复用七个已校验分区、97 个 packaged Overlay 和 24 个方法定位。真机状态 `NOT_RUN`。

证据口径：**ROM** = 本版本可复查的静态证据；**AOSP** = 固定源码对照；**外部** = 厂商公开说明或他版项目报告；**待验证** = 尚无足够静态或运行时证据。F 编号见[方法清单](../analysis/evidence/findings.json)，资源及 Overlay 见[扫描清单](../analysis/evidence/overlays.json)，组件与分区哈希见[组件](../analysis/evidence/components.json)及[解包记录](../analysis/evidence/extraction.json)，AOSP 文件和哈希见[固定源码清单](../analysis/evidence/aosp-sources.json)。

| 能力 | 入口 → 消费者（ROM） | 限制、作用屏和初始化 | 副作用 / 单独验收 |
|---|---|---|---|
| N1 独立外屏内容 | DMS → `SecondaryDisplayPolicy`，桌面资格 supplier 来自 `DesktopModeHelper`（F01–F06） | 内容模式相关 flag 已开；`config_isDesktopModeSupported` / `config_isDesktopModeDevOptionSupported` 基础值 false。资格属跨进程共用条件，DMS 在启动和设置变化时可恢复镜像；旧 `force_desktop` 路径受内容模式 flag 约束（F11） | 恢复镜像路径须保留；比对外屏 EXTERNAL 内容模式与内屏画面，避免把镜像误判为独立输出 |
| N2 原生次屏 HOME | `RootWindowContainer` 次屏 HOME 路径（F17）→ `config_secondaryHomePackage` 与 MiuiHome 的 `SecondaryDisplayLauncher` 声明 | `MiuiHomeLauncherResOverlay` 有品牌属性条件；实际 Overlay、按用户解析、Activity 创建及 Rust 实现待确认。适用目标是外接物理屏的 `TaskDisplayArea` | 记录有效包名、解析组件、HOME task 所属显示、拔插和主桌面回归；声明存在不能验收 |
| N3 独立应用任务 | `ActivityTaskSupervisor` 启动资格，`DisplayContentStubImpl` 屏幕差异处理（F09–F11、F18） | 同时受 display/TDA 和普通启动规则约束；背屏单独处理；动态 EXTERNAL ID 不能用 `id != 0` 替代 | 首个有状态实验使用系统现有 Activity；核对 task/display、焦点及退出，不改可信/私有/背屏规则 |
| N4 原生窗口管理 | `DesktopStateImpl` → Shell provider → 事件、任务、装饰组件；另有 MIUI `MiuiDesktopModeStatus`（F07、F08、F16） | Shell 在初始化缓存全局资格，另查每屏资格；MIUI desktop 状态受独立属性/设置影响。窗口处理者、动画与装饰归属待拆分 | 内屏手势、背屏、焦点、拔插与可调窗口分别验证；不并开两套全局能力 |
| N5 尺寸与黑边 | `ExternalScreenCompatManagerImpl` → `ActivityRecord` 配置与 Insets（F20、F21） | 默认关闭；应用配置/缩放和缓存不是外屏物理时序，也不是镜像 viewport；策略的外屏/包级条件待追踪 | 同时记录 viewport、逻辑尺寸/密度和应用 bounds；桌面和窗口路径稳定后单独测试 |
| N6 物理高刷 | 连接状态 → `DisplayModeDirectorImpl` → 全局 priority 24 RenderVote → 模式筛选（F12–F15、F22–F24） | 实际启用外屏、BSP 属性与 MIUI 优化影响投票，部分路径还受多屏标志约束；投票可能影响候选，未证实物理 60 上限。HWC 的 `hdmi_cfg_idx` 参数语义未闭合 | 核对 EDID/DRM 暴露模式、SF/HWC active mode 与显示器 OSD；解除渲染投票或逻辑显示 120 均不足以验收 |

## 对照与移植取舍

| 对照 | 可用结论 | 对本 ROM 的约束 |
|---|---|---|
| AOSP `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d` | 比较桌面资格、按显示的内容模式及 HOME/任务路径；桌面资格基础值 false 在 AOSP 也存在 | 不能把 false 单独归因为厂商删除功能；厂商证据来自实际注册的 MIUI provider、背屏分流、独立 Shell JAR、品牌 HOME Overlay 和渲染投票等 |
| [小米 Android 16 指南 §2.11](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2035) 与[工作台指南](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2034) | 官方为 Android 16 说明两套窗口能力有冲突风险；工作台示例针对 Pad | 可据此安排兼容性调查；不能外推为 Android 17 `popsicle` 的每一处限制或能力证明 |
| [HyperDesktopUnlock 固定提交的 README](https://raw.githubusercontent.com/the-marox/HyperDesktopUnlock/ee0c3d4d3abee7ab0f5a88f92cf82edb260ac948/README.md) | 他版报告列出系统连接对话框、镜像恢复、资格、可逆开关和诊断观测点 | 只用作对照。其主测试机是 Xiaomi 15，第三方 Dock 及自绘切换器超出目标；不照搬全局资格或非零 ID 判定，类定位须涵盖共享 Shell JAR，不屏蔽原生 HOME |

## 未解决项和执行顺序

1. **阶段 2 首要**：N2/N3/N4 补齐创建者、事件顺序、按显示条件和同一任务的监听/装饰/动画归属；区分真实执行边、仅声明、动态选择。确定 MiuiHome 启动绑定、次屏与主桌面进程/配置关系。
2. **阶段 2 并行的静态补项**：定位 N5 兼容策略的配置读取、更新和作用对象。N6 的 vendor 参数解析与任何设备模式测试暂不阻塞原生桌面。
3. **阶段 3 准入**：只有作用显示、缓存重建、任务归属和恢复路径有证据时，才为某一窗口路线给出最小候选；缺口保留为条件。禁止把关闭全局设备限制作为首个试验。
4. **阶段 4 才验证运行时**：有效 Overlay/资源、真实 EXTERNAL、HOME 解析、Shell 初始化/任务承载、KernelSU 环境和恢复路径，均待另行安排设备采集。
