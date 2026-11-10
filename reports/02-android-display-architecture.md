# 02 Android 17 原生显示架构

## 版本边界

ROM 元数据为 Android 17 / SDK 37。参考 AOSP `android17-release`，已固定 frameworks/base 提交 `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d`；下载文件哈希见 [aosp-sources.json](../analysis/evidence/aosp-sources.json)。这是相同 Android 主版本参考，**不声称是小米编译使用的精确提交**。以下均为 **[AOSP]**，本 ROM 的差异另见报告 03。

## 六项能力需要独立证明

| 能力 | 关键组件 | 后续判定证据 |
|---|---|---|
| 视频输出 | DP 驱动、HWC、SurfaceFlinger | 接收端有图像，热插拔与物理 mode |
| 独立逻辑 Display | LocalDisplayAdapter、LogicalDisplayMapper、DMS | 外接类型、唯一 ID、displayId、flags、content mode |
| 次屏应用 | ATMS、ActivityTaskSupervisor、DisplayContent | 指定 displayId 启动后 Activity/task 实际归属 |
| 独立桌面 | secondary HOME、WM Shell、SystemUI、任务组织器 | HOME 解析、任务栏、窗口装饰、焦点与恢复 |
| 外屏分辨率 | EDID、HWC modes、SF、DMS/WMS | supportedModes 与活动物理 mode；逻辑尺寸分别记录 |
| 外屏高刷 | 链路、HWC、SF、DisplayModeDirector | 外屏物理 mode、实际时序和接收端 OSD 交叉核实 |

镜像有图像不能证明具备桌面。`wm size` 的逻辑尺寸、渲染 FPS、虚拟 Display 刷新率也不能证明物理输出 120 Hz。

## 热插拔、逻辑显示与镜像

`LocalDisplayAdapter` 接收物理显示连接，读取 SurfaceControl 的静态/动态显示信息，建立模式表。该版本 `getDisplayDeviceInfoLocked()` 为外接输出设置 EXTERNAL / PRESENTATION，物理显示通常设 TRUSTED，但仍检查端口私有策略；不能对任意虚拟屏套用这些属性。

`LogicalDisplayMapper` 为设备建立逻辑显示并发出显示事件，DMS 向上层发布。WindowManager 为可管理的 Display 建立 `DisplayContent` 和 TaskDisplayArea。displayId 是运行时分配结果，未来脚本必须发现外屏 ID，不能硬编码为 1（设备还有背屏）。

Android 17 参考分支新增内容模式管理路径：DMS 使用 `SecondaryDisplayPolicy` 与 `DesktopModeHelper.canEnterDesktopMode()`。`forceEnableMirrorBuiltInDisplaySettingIfNeeded()` 在设备不支持 desktop 时会把 secure 镜像设置恢复为开启；`getPolicyAwareConnectionPreference()` 会把不再支持的 DESKTOP 偏好恢复为 ASK。这些是本版本上游行为，不能直接归因于 HyperOS 屏蔽。

参考：[DMS](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/display/DisplayManagerService.java)、[SecondaryDisplayPolicy](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/display/SecondaryDisplayPolicy.java)。

## 桌面开关不是单一布尔值

`DesktopModeHelper.canEnterDesktopMode()` 组合设备资格、`ENABLE_DESKTOP_WINDOWING_MODE` 与开发者强制开关。资格涉及 `config_isDesktopModeSupported`、`config_isDesktopModeDevOptionSupported`、`enableDesktopModeThroughDevOption()`；`persist.wm.debug.desktop_mode_enforce_device_restrictions` 默认 true，且在类初始化读取。内屏能否承载 desktop 又由 `config_canInternalDisplayHostDesktops` 单独控制。

`DesktopModeFlags` 将 aconfig 和开发者开关结合，并缓存覆盖状态；源码注释明确预期重启生效。资源 false 或 Shell 类存在都不是整体功能的充分条件；DeviceConfig 也不是任意 aconfig 的通用替代。

WM Shell 的 `DesktopTasksController`、`DesktopDisplayEventHandler` 依赖 `DesktopState`，负责 desktop task 迁移和显示事件。SystemUI 是否构建这些组件、依赖注入是否创建、实际 flags 是否开放，都要读 ROM。`Freeform` 窗口能力与完整桌面体验也需分别确认。

参考：[DesktopModeHelper](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/wm/DesktopModeHelper.java)、[DesktopModeFlags](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/core/java/android/window/DesktopModeFlags.java)、[DesktopTasksController](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/libs/WindowManager/Shell/src/com/android/wm/shell/desktopmode/DesktopTasksController.kt)。

## 次屏 Activity 与 HOME

公开 `ActivityOptions.setLaunchDisplayId()` 表达启动意图，仍经 `ActivityTaskSupervisor.isCallerAllowedToLaunchOnDisplay()` 校验。参考分支检查显示存在、非 REAR、内容模式允许承载任务，以及权限、trusted/private、显示所有者、用户可见性。普通应用不能通过 API 绕过这些限制。

`RootWindowContainer.shouldPlaceSecondaryHomeOnDisplayArea()` 检查 canHostHomeTask、多显示支持、设备已配置、CE 存储已解锁、显示有效和 HOME 支持；新内容模式启用时还检查 canHostTasks。ATMS `getSecondaryHomeIntent()` 以 SECONDARY_HOME 解析，可由配置选择系统指定 launcher。它与普通主屏 HOME 是不同入口。

WMS 的 `DisplayWindowSettings` 为每个显示维护 windowing mode、system decors、HOME、IME、密度、尺寸与焦点策略。可显示 Activity 不代表可以显示 HOME、任务栏或屏幕键盘；调用相应管理接口也可能需要系统权限。

参考：[ActivityTaskSupervisor](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/wm/ActivityTaskSupervisor.java)、[RootWindowContainer](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/wm/RootWindowContainer.java)、[DisplayWindowSettings](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/wm/DisplayWindowSettings.java)。

## 模式、刷新率与输入

模式从显示接收端/驱动经 HWC 和 SurfaceFlinger 上报，`LocalDisplayAdapter` 构造 Android supportedModes；DisplayModeDirector 汇总投票/约束，再向底层提交 desired mode specs。约束能减少或选择已暴露模式，不能凭空增加链路不支持的时序。EDID、DP lane/link rate、色深、转接器能力必须另取硬件证据。

输入链路独立于输出链路。InputManagerService 提供端口/唯一 ID 到显示的关联接口，受相应权限控制；鼠标跨屏、焦点、键盘目标、IME、手柄焦点要分别测。手机触摸继续操作内屏也需要同时验证。

参考：[LocalDisplayAdapter](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/display/LocalDisplayAdapter.java)、[DisplayModeDirector](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/display/mode/DisplayModeDirector.java)、[InputManagerService](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/input/InputManagerService.java)。
