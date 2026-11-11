# 12 次屏 HOME 的窗口参数与应用落屏

2026-11-11，`OS4.0.6.0.XPBCNXM`。已定位窗口创建回调收到的显示信息及指标向量，并核对 Framework 选择应用启动显示区的顺序。MiuiHome 次屏点击到普通应用启动的调用边仍未定位。设备验证 `NOT_RUN`。[输入哈希与定位证据](../analysis/evidence/native-desktop-stage2.json)

## 窗口创建回调

`libhyper_os_ui_private.dylib.so` 中 `WindowController.handle_surface_callback` 读取当前窗口 display ID，以它查根显示信息，再构造 `WindowDisplayInfo`。窗口创建分支在 `0x1a6f10` 通过 `UiWindow` 表的 `+0x20` 槽传入 `NativeWindow`、`WindowDisplayInfo` 和一个指标向量。独立的 `SurfaceView.on_surface_created` 路径处理该窗口下的子视图。[回调槽位](10-native-secondary-home-lifecycle.md)

次屏 HOME 的 `+0x20` 槽指向 `libapp_launcher.so` 的 `0x77a110`。上一检查点的间接调用 `0x77a130` 从指标向量的 `+0x18` 字段取表指针，再调用表内 `+0x18` 槽。运行库在 `0x1a6ee0` 为该字段选用 `0x230840`，其 `0x230858` 处的 `R_AARCH64_ABS64` 重定位指向 `destructor_vec<MetricsEntry>`（`0x17d504`）。回调随后释放 `WindowDisplayInfo` 和 `NativeWindow`。这段直接路径的作用是释放三个传入参数。实际界面构建与显示参数的后续消费者仍待定位。

## HOME 和应用的启动目标

| 路径 | 已确认的显示来源 |
|---|---|
| 系统启动 HOME（N30） | `ActivityStartController.startHomeActivity` 从目标 `TaskDisplayArea` 同时写入 `ActivityOptions.setLaunchDisplayId` 与 `setLaunchTaskDisplayArea`，再提交给 `ActivityStarter` |
| 系统为普通应用选择显示区（N31） | `LaunchParamsUtil.getPreferredLaunchTaskDisplayArea` 先检查显式显示区 token、feature ID、display ID，再按条件参考无显示来源的 handover、来源 Activity、既有 task、caller display 和当前参数。已有可见任务可改变来源 Activity 的优先级。仍需通过多显示、HOME 和其他启动检查 |
| MiuiHome 通用原生启动 | `libapp_launcher.so` 的两处直接调用进入 `Scene_start_activity`。运行库将参数传给 `scene::activity::start_activity`，可查询 `Runtime.component_token` 并调用 `IActivityManager`。同一运行库另有写入 `launchDisplayId` 的 setter，当前 Launcher 的动态符号表中未见对该 setter 的直接导入。参数也可能来自传入的 Bundle 或其他启动入口 |

从 Launcher 的 `.text` 枚举到 `Scene_start_activity`、`Scene_start_activity_from_recents` 和 `LauncherApps_start_main_activity` 的直接分支，并追查部分 wrapper 调用者。`0x94c794` 构造 `RecentsActivity`，`0xd4a02c` 的目标是 `SafeLauncher`。`0x5d2cc0` 与 `0x5d2c04` 位于小窗 API 路径，分别进入 Scene 与 LauncherApps wrapper，该函数会从 MIUI 小窗 helper 获取 options 或设置窗口模式与 bounds。以上路径尚未与 `SecondaryDisplayLauncherUi` 的点击处理相连。枚举范围限于直接分支、命名导入和本次复查的调用者，间接调用和 Flutter AOT 的启动来源仍开放。

后续离线从次屏窗口描述符的其余事件槽及 Flutter 桥接入口定位应用点击处理。设备阶段如安排验证，分别记录首次启动和已有可见任务两种情况。关联 HOME 实际 display/TDA、应用启动的来源 token 或 options、目标任务最终 display，并对照 Framework 的显示区选择原因。[条件设计](09-native-desktop-minimal-design.md)

复查使用 NDK `llvm-readelf -rW`、`--dyn-syms --wide` 和定向反汇编。运行库的 `.rela.dyn` 使用 Android `APS2` 编码。`python scripts/verify_native_desktop.py --local` 可核对原始库哈希、直接分支目标、`MetricsEntry` 析构函数与 `BpActivityManager.startActivity` 的命名重定位，以及 N30/N31 方法锚点。反汇编切片与调用扫描保留在本地 `analysis/local/next-*`。
