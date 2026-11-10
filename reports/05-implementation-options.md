# 05 功能补全路径评估

本轮交付研究与验证设计，不生成安装模块、不 Hook、不操作设备。以下方案的可行性依据报告 03/04 的 ROM 证据，均未通过真机验收。

## 建议顺序

先用只读信息确认外接物理 Display、资格/镜像状态、模式表和 priority 24 渲染投票；再用独立应用验证次屏 Activity。若能力存在，优先以最小资源/配置改动接通外屏桌面；只有确认某个低频策略仍阻断时，再设计单点 Hook。物理高刷单独验证，不作为桌面成功的附带结论。

| 路线 | 静态依据 | 当前评价 | 进入下一步所需证据 |
|---|---|---|---|
| A 已有原生配置 | 桌面/投射/内容模式 flag 为 true，资格资源为 false | 优先研究，尚不可直接部署 | 实际 Overlay 值、Shell 资格、外屏 flags/content mode |
| B 可逆 KernelSU 配置模块 | 可在启动时提供配置覆盖，保留原系统镜像 | 可作为配置载体，需验证模块机制 | 当前 KernelSU 版本、挂载/Overlay 能力、恢复方式与完整测试 |
| C Framework 单点 Hook | 已定位 helper、镜像恢复及刷新率投票路径 | 配置不足时才考虑 | 拒绝原因、精确进程/方法、调用频率和最小作用域 |
| D 独立外屏应用 | ROM 保留多显示校验，EXTERNAL 并非一律拒绝 | 最适合先做能力探针 | 可见公共外屏、可启动 Activity、输入/任务分离 |
| E HWC/内核修改 | 有 pluggable 模式接口与厂商显示库 | 暂不制作补丁 | EDID、DRM/HWC modes、链路/并发限制、对应源码 |

## A：配置层的候选及限制

1. **桌面资源资格**：最小候选为 `config_isDesktopModeSupported`。保留 `config_canInternalDisplayHostDesktops=false`，以控制内屏参与范围；是否真正只影响外屏仍需测量。需要开发者覆盖时再评估 `config_isDesktopModeDevOptionSupported`，不默认全部改 true。RRO 必须满足本版本 overlayable、签名/分区策略及 idmap 约束，不能保证普通 APK 安装即可覆盖 framework 私有资源。
2. **镜像内容模式**：在桌面资格和实际 EXTERNAL 显示条件满足后，才研究 secure `mirror_built_in_display`；仅写 0 会被已定位的策略恢复。确认/连接偏好与 system decors 也要一起观察。
3. **设备限制属性**：`persist.wm.debug.desktop_mode_enforce_device_restrictions=false` 在 helper/Shell 的源码上可绕过资格限制，但其作用范围包含内屏，并且有类/构造时缓存；因此更适合作为后续有恢复措施的诊断对照，优先级低于有选择的资源覆盖。
4. **开发者入口**：当前版本有 DesktopExperience 分支，不能照搬旧 Android Global 键或随意写 DeviceConfig。先核实 consumer，再决定配置载体。
5. **刷新率策略**：修改 `support_builtin_high_fps_when_pluggable_connected` 会同时影响 Framework 策略和底层显示库，不能仅作为 GUI 高刷开关。先查实际投票、模式与并发能力，再设计单变量对照；不关闭温控和全部 MIUI optimization。

这些改动可能需要 framework/SystemUI 进程重新初始化；正式验证应按“需要重启”处理。模块构建前需先证明资源能被合法应用，并明确移除覆盖、还原设置和缓存后的恢复流程。

## B：KernelSU 仅作为可逆载体

可研究 systemless 的资源 Overlay 或启动时配置，采用 ROM fingerprint/SDK/文件哈希门控：版本不符时不生效；默认关闭、一次只启用一组改动，日志写本地，并保留独立关闭入口。

当前只知道用户使用 KernelSU Official，未读取设备上的实际版本、模块挂载组件和恢复配置。不能假设 Magisk 的 resetprop/挂载实现或另一 KernelSU 分支功能必定存在；具体实现必须对照未来采集结果。卸载或禁用模块也未必自动清除已经写入的 persistent property/Settings，要保存原值并显式恢复。

本阶段没有模块目录、刷写内容或安装包。后续制作时应附一份与具体设备状态对应的恢复说明；不得先改 boot/system 分区来“试试看”。

## C：Hook 的候选位置与边界

| 候选 | 目标进程 | 为什么可能有用 | 主要风险与限定 |
|---|---|---|---|
| DesktopModeHelper 的资格判断 | system_server | 若资源无法覆盖，精确验证资格拒绝 | helper 为全设备判断，容易影响内屏；不能作为最终精细策略的充分方案 |
| SecondaryDisplayPolicy 的低频镜像策略 | system_server | 观察或验证被恢复为镜像的原因 | 强迫关闭镜像可能得到黑屏/空桌面，必须先有 HOME/Shell 与 app 启动能力 |
| DesktopStateImpl 构造/组件创建条件 | SystemUI / WM Shell 所在进程 | 与 framework 的资格同步 | 依赖注入、Optional、初始化顺序可能崩溃；只改一侧会不一致 |
| DisplayModeDirectorImpl 的条件性投票 | system_server | 已定位 60 render vote 的来源 | 不可全局删除刷新率/温控投票；应限于已确认的外屏场景并保留其他约束 |

仅对本 ROM 哈希与方法签名生效，先做有界日志观测，确认调用频率和返回值，再讨论改变行为。若支持启动时开关，默认不改变返回值；异常自动停止变更。一次仅验证一个点，重启/移除 Hook 后对照基线。

禁止大范围改 `isCallerAllowedToLaunchOnDisplay()` 恒 true、绕过 REAR/private/trusted 校验，或 Hook 主 Launcher 的每帧渲染、动画、布局。这些既无必要证据，也会重现已知性能与错位风险。Framework Hook 还存在 system_server 崩溃/启动循环风险，必须先具备本版本可用的模块禁用与恢复路径。

## D：独立外屏应用与权限分工

| 身份 | 可研究的能力 | 仍需系统能力或额外授权 |
|---|---|---|
| 普通应用 | DisplayManager 枚举可访问显示；Presentation 显示自己的 UI；ActivityOptions 指定可访问公共显示；声明 SECONDARY_HOME 候选 | 系统实际是否允许承载任务/选择 HOME；任意第三方窗口嵌入、任务组织、输入注入、系统装饰管理 |
| Root 应用 + 独立辅助进程 | 经明确授权执行诊断/启动命令，研究受控的特权代理 | App 本体不会自动变成 system UID；Binder 身份、签名权限、SELinux、hidden API 都要实际核验 |
| 平台签名/特权系统组件 | 在正确权限、allowlist/角色和系统集成下管理更多任务/窗口能力 | 不是放入 priv-app 就自动取得所有权限；需版本适配、任务组织器与 UI 生命周期支持 |

首个探针应只显示自己的测试 Activity：显示实际 displayId、uniqueId/type、逻辑尺寸和输入目标；由显式操作启动少量可调整大小的测试应用，记录 task 所在 Display。普通应用可以是外屏启动器，但不能承诺把任意第三方 Activity 嵌入自己的 Surface 中实现完整桌面窗口管理。

若 ROM 原有 SECONDARY_HOME 能正常工作，可优先复用；若 Launcher 原生实现不能满足需求，独立外屏启动器能避开主 Launcher 渲染路径，但自由窗口、任务栏与窗口装饰仍依赖可工作的 WM Shell/系统权限代理。

## E：底层路径的准入条件

只有出现“接收端 EDID 宣告高刷、链路条件满足，而 DRM/HWC 模式被明确裁剪/拒绝”的证据后，再评估底层。需要与本 ROM 一致的 Qualcomm 显示驱动/内核源码、设备树/DTBO、DP PHY/控制器配置及厂商 composer 版本。公开通用源码或其他机型补丁不能证明适用。

潜在风险包括 DP 训练失败、黑屏、热/功耗升高、双内建屏并发限制、色深/DSC/带宽不匹配与启动失败。当前不补丁二进制、不改 DTBO、不刷内核；也没有支持任意 120/180 Hz 的承诺。

## 可进入实现阶段的条件

完成报告 06 的只读基线，确认外屏 ID、实际资源和投票后，才能确定最小可实施路线。当前推荐顺序为 **D 的能力探针 → A 的最小配置对照 → B 的可逆载体**；C/E 保留为有证据触发的后续选项。独立桌面与物理高刷分别验收。
