# 03 HyperOS 定制与限制定位

对象：popsicle / OS4.0.6.0.XPBCNXM / Android 17。本文均为静态研究，**没有真机验证**。

结论：ROM 保留了多显示器与大批桌面组件；已定位桌面资格、镜像恢复、旧接口失效及背屏特殊处理的具体路径。现有证据支持先验证配置和独立次屏应用，不支持“完整桌面已被删除”或“改一个属性就能全部恢复”的结论。

## 证据如何复查

原文件哈希见 [components.json](../analysis/evidence/components.json) / [input-copies.json](../analysis/evidence/input-copies.json)。F01–F24 对应 [findings.json](../analysis/evidence/findings.json)：含类名、方法锚点、**本地反编译文件**行号和哈希。行号不是小米原始源码行号。完整反编译代码仅保存在 `analysis/local/jadx/`，不提交公共仓库。

**[ROM] F19/F20**：生成的 MiuiImplManifest 将 DisplayModeDirectorStub、DisplayManagerServiceStub、DisplayContentStub、ActivityStarterStub、ExternalScreenCompatManagerStub 注册到相应 Impl.Provider；结合 services 的 stub 获取和调用，建立了厂商扩展的静态绑定关系，而非仅凭同名类推断。

JADX 全量 services 有 73 个错误，选定 numeric 运行也有个别不相关失败；不能把错误方法当成正确 Java。桌面资格与镜像策略另做 fallback 指令视图检查，错误数 0。关键资源不采用 JADX 自带 SDK 的 `android.R` 名称，而用本 ROM 的 aapt2 数值映射交叉确认。

## 一、桌面资格门控已定位

**[ROM]** framework-res 基础资源：

| 资源 | ID | 默认值 |
|---|---|---|
| config_isDesktopModeSupported | 0x011101f7 | false |
| config_isDesktopModeDevOptionSupported | 0x011101f6 | false |
| config_canInternalDisplayHostDesktops | 0x0111006f | false |
| config_supportsMultiDisplay | 0x011102b8 | true |
| config_supportsMultiWindow | 0x011102b9 | true |
| config_supportsSystemDecorsOnSecondaryDisplays | 0x011102bd | true |

这些 false 同样存在于所固定 AOSP 的基础配置，**不能仅据默认值认定小米添加了独有封锁**。扫描七个已解分区内全部 97 个 packaged Overlay，没有发现上述三个桌面资格资源的具名覆盖项；所有资源和 manifest dump 成功，见 [overlays.json](../analysis/evidence/overlays.json)。不包括运行时下载的 Overlay、用户改动、实际 idmap/启用状态；这些仍需真机检查。

**[ROM] F04/F05**：framework 中 relocated flags 的方法体返回 `enableDesktopWindowingMode=true`、`enableProjectedDisplayDesktopMode=true`、`enableDisplayContentModeManagement=true`，而 `enableDesktopModeThroughDevOption=false`。因此“代码核心开关全关”不符合本 ROM。

**[ROM] F01**：`DesktopModeHelper.isDeviceEligibleForDesktopMode()` 读取资源和设备限制属性；`canEnterDesktopMode()` 再组合 desktop flag/开发者覆盖。`persist.wm.debug.desktop_mode_enforce_device_restrictions` 默认 true，在类初始化读取。

**[ROM] F07/F08**：`Miui-WindowManager-Shell.jar` 的 `DesktopStateImpl` 构造函数读取同一组数值资源并缓存 `canEnterDesktopMode`；外接支持还检查 `WindowManager.isEligibleForDesktopMode(displayId)`。`WMShellModule.provideDesktopDisplayEventHandler()`、`provideDesktopDisplayModeController()` 等在资格为 false 时返回空 Optional；这已经从“类存在”追到了“创建组件的条件”。

**[推测]** 在资源默认值、属性默认值及无运行时覆盖的前提下，framework 和 Shell 的桌面资格会被拒绝。配置层是合理的首个研究方向，但不能宣称已经确认设备运行时条件或完整依赖链全部满足。

## 二、为什么旧开关可能不生效

**[ROM] F02/F03** 调用链：

`DisplayManagerService` 构造 SecondaryDisplayPolicy → supplier 调用 injector → `DesktopModeHelper.canEnterDesktopMode()` → 开机处理及 `SettingsObserver.onChange()` 调用 `forceEnableMirrorBuiltInDisplaySettingIfNeeded()` → 桌面不支持时把 secure `mirror_built_in_display` 恢复为 1。

这意味着写 0 后被恢复，可能是原生资格策略执行，不一定是某个 Launcher 主动改回。必须同时记录写前/写后、日志及资格条件。

**[ROM] F11** `DisplayContent.isPublicSecondaryDisplayWithDesktopModeForceEnabled()` 在新内容模式管理 flag 为 true 时直接返回 false；旧 `mForceDesktopModeOnExternalDisplays` 路径不能因此被当成适用本版本的完整方案。

**[ROM] F06** `DesktopModeFlags` 优先走新的 DesktopExperience 开关。`DesktopExperienceFlags.isToggleOverriddenBySystem()` 使用 `persist.wm.debug.desktop_experience_devopts`，且在内容模式管理开启时还要求 `config_isDesktopModeDevOptionSupported`。所以旧 Global 开发者键存在并不表示被当前分支采用。开关和 Shell 资格有进程缓存，重启后的状态也要单独验证。

## 三、背屏不是外接屏

**[ROM]** `odm/etc/build.prop:223` 指定 `persist.sys.secondary_builtin_display_id=1`，并有双内建显示配置。

**[ROM] F09** `ActivityTaskSupervisor.isCallerAllowedToLaunchOnDisplay()` 先检查 REAR flag / canHostTasks，再检查系统权限、可信/私有属性与用户可见性；还插入了 displayId 1 的 `ActivityStarterStub.isShouldShowOnRearDisplay()` 路径。它不是对所有 EXTERNAL display 的统一拒绝。

**[ROM] F10** `DisplayContentStubImpl.desktopModeForceDisabled()` 与 `shouldNeverShowSystemDecorations()` 对独立背屏/翻盖设备的 ID 1 作特判。不能把这些判断一并绕过，也不能固定对 displayId 1 启动测试应用。

**[ROM] F11/F17** HOME 需要 canHostHomeTask、系统配置完成、解锁/厂商背屏例外、有效 display、HOME 支持及 canHostTasks；desktop 资格还检查 system decors、Freeform、content mode switch。应用启动、HOME、系统装饰分别受不同条件控制。

## 四、SystemUI / Launcher 确实有次屏入口，但行为尚未完全证明

**[ROM]** MiuiSystemUI manifest 要求 `com.miui.wm.shell` 库；该库的配置指向 `Miui-WindowManager-Shell.jar`。该 JAR 定义 DesktopTasksController、DesktopDisplayEventHandler、DesktopModeWindowDecorViewModel 和 Dagger 创建方法，SystemUI manifest 还声明 DesktopWallpaperActivity。已追踪关键创建门控，尚未证明所有运行时依赖实际被实例化。

**[ROM]** MiuiHome manifest 声明导出的 `com.miui.home.launcher.SecondaryDisplayLauncher`，intent category 为 SECONDARY_HOME，launchMode 为 1。`MiuiHomeLauncherResOverlay.apk` 静态覆盖 android 的 secondary HOME package/component，条件是 `ro.miui.product.home=com.miui.home`；POCO 版本使用另一条件。`system_ext/etc/init/init.miui.ext.rc:414–419` 依据品牌设置该属性，Xiaomi 分支指向 com.miui.home。仍以未来设备上 resolve-activity / overlay lookup 的实际结果为准。

**[ROM]** MiuiHome APK `android:hasCode=false`、没有 `classes*.dex`；它依赖 `hyperos.rustruntime.v5`，包含 `libapp.so`、`libapp_launcher.so` 等原生载体。运行时 JAR 仅定义一个 Empty 类。`libapp_launcher.so` 是 AArch64 ELF，其中偏移 2,511,504 有 SecondaryDisplayLauncher 名称线索；**字符串不是方法实现或可用性证明**。本轮未完成该原生实现的调用关系恢复，不能据此判断它能否独立承载应用窗口或完整任务栏。

这也意味着不应继续假设旧版本 Java Launcher Hook 点在当前版本仍有效。优先避免侵入主 Launcher 的动画、布局、绘制路径；独立外屏应用可先验证，完整系统桌面仍依赖 WM/Shell 的任务管理能力。

## 五、MIUI 自有 desktop 分支需要另看

**[ROM] F16** `MiuiDesktopModeStatus` 在类初始化读取 `ro.config.miui_desktop_mode_enabled`（默认 false），活动状态另读 `miui_dkt_mode`。`MiuiWMShellModule` 在未启用时返回 stub 实例；这与 Android 原生 DesktopState 门控是不同路径。已扫描的文本配置未找到该属性的显式赋值，运行时值尚未测量；不能凭相似命名认定它就是外屏独立桌面的开关。

## 六、输入与权限边界

SystemUI/Shell 具备系统权限，而普通外屏应用不能任意注册全局任务组织器、嵌入第三方应用或注入输入。Root 可启动有授权身份的辅助进程，但应用进程不会仅因手机已 Root 就自动获得 Binder 系统权限。手柄焦点、跨屏鼠标、独立 IME、内屏触摸互不干扰均列入待真机验证；本轮不声称已完成输入支持。

## 七、外屏应用缩放有单独的厂商路径

**[ROM] F20/F21**：ExternalScreenCompatManagerStub 注册到 ExternalScreenCompatManagerImpl；WMS 获取该实例，ActivityRecord 在解析配置时调用 `shouldApplyScaling()` / `applyScaleConfiguration()`，InsetsPolicy 也读取其状态。实现以 `persist.wm.external_compat.enabled`（默认 false）门控，并有按 Activity 配置、缩放状态和缓存。完整缩放策略及控制器配置尚未恢复，不能声称该属性能解决镜像黑边或更改物理输出分辨率。

这个路径涉及 Activity 配置与 Insets，不是低频热插拔开关。本轮只记录、未启用，也不建议把它作为绕过主 Launcher 性能问题的首个 Hook 点。

## 尚未解决的问题

- 实机的 Overlay/idmap、属性、DesktopState、content mode 和 system decors 状态。
- Launcher 原生 SECONDARY_HOME 的具体渲染、应用启动与桌面容器行为。
- 自有 MIUI desktop 分支是否含本设备可用的完整实现。
- 次屏实际模式表、带宽、EDID、内外屏并发时的 HWC 选择与功耗。
- SystemUI 连接提示的部分协程反编译失败，未据失败方法推导交互结论。

下一步的实施比较见 [05](05-implementation-options.md)，证据最强的刷新率策略见 [04](04-display-refresh-rate.md)。
