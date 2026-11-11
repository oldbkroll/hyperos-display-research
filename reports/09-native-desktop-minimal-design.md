# 09 原生外接桌面：最小改动条件设计

2026-11-11，原生计划阶段 3。**已形成条件设计；路线未选定，实施准入未通过（`PARTIAL`）。** 真机阶段 `NOT_RUN`。本报告无补丁、模块、Hook 或设备命令执行。编号 N1–N6 是[能力矩阵](07-native-desktop-evidence-matrix.md)；具体调用链与 N01–N17 锚点见[报告 08](08-native-desktop-call-chain.md)和[证据清单](../analysis/evidence/native-desktop-stage2.json)。

## 路线决策

共同底座是 **现有外屏启用和任务承载 + MiuiHome 次屏 HOME**。先只验证这两项，保留 stock 窗口组件与设置；独立 Activity 成功只计 N3，原生 HOME 可用另计 N2，均不自动计作 N4。

| 路线 | 已有证据 | 选定之前的必要证据 | 当前决策 |
|---|---|---|---|
| A：MiuiHome + MIUI 窗口 | MIUI listener 真实存在；部分服务方法按 task 的 display 查询，但手势控制器有默认屏依赖，桌面另有资格 | 证明目标 EXTERNAL 的创建、焦点、装饰、bounds 和拔屏恢复能走 MIUI 路径，且内屏手势及背屏保持基线 | 优先评估；未选定 |
| B：MiuiHome + AOSP WM Shell | 桌面组件和依赖图存在；初始化资格有缓存，AOSP 与 MIUI 接收同一 task 通知 | 对同一 task/transition 确认两路处理职责与先后顺序，证明目标屏可获得所需组件且内屏不被带入桌面；若两路会写同一对象，先定位协调点 | 保留候选；未选定 |

两个路线都缺少次屏 HOME 的生命周期及配置传播证据。路线 A 的静态证据不足，不自动切换 B；保留独立输出或单个 Activity 的阶段结果，不用第三方桌面替换原生目标。

后续静态检查已定位次屏 HOME 的九个回调槽位。应用启动和 `on_surface_created` 中的间接调用仍待追踪。共享装饰 provider 优先选择启用的 MIUI 实现，路线 B 的准入增加对真机绑定和实际装饰调用的核对。[次屏生命周期](10-native-secondary-home-lifecycle.md) · [外屏窗口归属](11-native-desktop-window-ownership.md)

## 候选变量与验证顺序

表中每行是独立对照，只在对应阻断被观测到后才考虑。一次只改变一项，出现预期外影响就回到同一基线。

| 实验 | 触发证据 | 最小对象 / 预期状态 | 影响与恢复 |
|---|---|---|---|
| D0 只读基线 | 设备操作范围另行确认 | 断开和连接镜像各采一次；记录实际 EXTERNAL、当前用户、Overlay、资格、HOME 与 Shell/任务/物理模式 | 不写入；设备版本或外屏身份不匹配时只存差异，不进入下一行 |
| D1 系统 Activity / 次屏 HOME | D0 能可靠识别外屏并保存基线 | 优先在原设置下观察、再经授权启动系统已有 Activity；核对 task 是否在实际 EXTERNAL。随后验证系统 HOME 解析、创建和拔插 | 启动会改变 task/焦点；结束测试任务、返回原镜像选择并重采。拒绝先记录实际原因 |
| D2 连接入口 | 当前被拒仅源于对话框资格；已核对实际 `DesktopState` 与 kiosk 状态 | 首选 ROM 已有的用户配置或系统入口。入口假设只检验 Desktop 选择是否可达并调用原连接逻辑，不改变 HOME、任务授权或物理模式 | 入口可见不代表外屏可用；若没有原生配置入口，记录缺项，不先做 UI Hook |
| D3 资格配置 | D0/D1 指向 Framework 与 Shell 资格，且具备可恢复启动方式 | 仅评估有效 `config_isDesktopModeSupported` 或 dev option 资源之一作为单变量对照；检查生效资源来源、两进程资格与每屏结果；保留内屏桌面资格为 false | 这些资源是全局输入，可能影响两进程和默认屏；核对缓存重建和实际 Overlay 支持后才能试验。移除候选配置并重建原进程状态，再核对开关、设置和屏幕行为 |
| D4 镜像策略 | 已验证同一外屏的连接选择写入被原策略恢复，且 D3 不能解决 | 优先使用现有受支持配置；分别记录用户选择、写入时序、DMS 恢复的条件与结果。该策略依赖全局镜像状态，没有显示参数的接口不可声称外屏专属 | 必须能区分原始镜像选择与策略恢复，并保留用户返回镜像的路径。无法限定作用范围则不做 Hook 或持久改动 |
| D5 窗口管理 | 原生 HOME/任务可用，路线 A 或 B 已按上表准入 | 按 `taskId + displayId + transition` 对照接收者与实际写入者；分别验证装饰、resize、最大化、焦点和拔屏 | 同一任务出现重复操作、默认屏异常、崩溃或无法恢复，撤销当前变量并暂停。尺寸和高刷继续单列 |

## 进程、配置与初始化兼容表

| 载体 / 运行位置 | 静态锚点 | 实施前核对 |
|---|---|---|
| `services.jar` / `system_server` | `DesktopModeHelper`、`SecondaryDisplayPolicy`、`RootWindowContainer`、`TaskOrganizerController`（F01–F03、N01/N02/N05） | ROM 指纹、文件哈希、实际定义类加载器和方法签名；在 DMS/ATMS 创建后核对资格 supplier 与 observer。拒绝以改任务权限、私有/可信或背屏校验解决资格问题 |
| `MiuiSystemUI.apk` / SystemUI | `ConnectingDisplayViewModel` 和 `ExternalDisplayConnectionDialogDelegate`（N03/N04/N13） | 对话框真实状态、kiosk、待连接 ID、用户选择及 `DesktopState` 实际类型；记录是否按首连、记忆选择或重连分支执行 |
| `Miui-WindowManager-Shell.jar` / SystemUI 的共享库 | `DesktopStateImpl`、`WMShellModule`、`ShellTaskOrganizer`、MIUI `MultiTaskingTaskListener`（F07/F08、N06–N09/N14） | 共享库真实类加载器和签名；`DesktopStateImpl` 资格何时缓存、providers 与 ShellInit 何时执行。运行时重新读出资格不代表创建了之前缺失的 Optional 组件 |
| `MiuiHome.apk` 与 `libapp_launcher.so` / MiuiHome | manifest `SECONDARY_HOME`、native 名称分派、共享 runtime（报告 08） | 有效 HOME 解析、Activity 进程、目标 Display/TDA、内外屏配置与恢复。默认进程声明和 ELF 地址不替代运行证据；不改主 Launcher |

若后续需要载体，只读诊断与行为修改独立交付，默认关闭并提供独立停用方式。仅允许匹配已验证指纹和输入哈希的组合，目标屏必须由当前会话中的物理 EXTERNAL 身份确认，不能以非零 ID 替代。进程/类/方法/用户/显示变化或识别不全时保持原行为。诊断只记录必要的版本、用户、显示、事件原因、顺序和任务标识，限长并保留本地；不记录应用内容。KernelSU Official 版本、模块能力及实际可用的恢复方式都需 D0 后核对。

每个候选变更执行前保存配置键是否存在及原值、Overlay 原状态、是否需重建进程、实验前内容模式、内屏/背屏状态；恢复时还原原值或删除原来不存在的键，重建并重新采集。出现内屏手势失效、背屏异常、系统崩溃、黑屏/重启或无法回到基线，停止叠加，先按该变量的恢复路径处理。在恢复方式验证前不装模块。

## 交接到阶段 4

使用[只读验证预案](06-device-validation-plan.md)的基线部分，另行确认设备操作范围后再运行采集器。关注四个未关闭项：有效资格与显示身份、实际 HOME 解析/配置、Shell 初始化与任务写入归属、恢复能力。先保存缺失、拒绝和原始日志路径，再决定是否安排有状态实验。阶段 2 中尚可离线追踪的原生回调及窗口事务继续留作独立任务；本次不因写出设计而升级阶段状态。
