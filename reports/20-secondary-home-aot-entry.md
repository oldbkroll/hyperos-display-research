# 20 次屏 HOME 的 Flutter AOT 入口与窗口归属

2026-11-12（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`，从 `4ba2b27` 续查。复用同版 ROM 和 D10 归档，新增真机验证为 `NOT_RUN`。[AOT、Rust 与窗口运行库锚点](../analysis/evidence/native-secondary-aot.json) · [D10 归档锚点](../analysis/evidence/native-first-frame.json)

**[ROM] 已确认原厂 Launcher 有 Flutter 多视图实现。已定位的次屏 HOME 生命周期没有创建 Flutter scene，也没有把自己的窗口交给既有 scene。** 多视图可在已运行的 scene 下创建附属窗口，实际落屏由该 scene 或父窗口的运行上下文决定。当前找不到一个能直接复用、同时接收次屏 HOME 的 token、Surface 和显示指标的原厂入口。这个缺口位于 MiuiHome 内部，路线 A 和 B 都依赖它。[渲染宿主](19-secondary-home-render-host.md) · [两条路线的准入条件](09-native-desktop-minimal-design.md)

## [ROM] Dart 启动与 Rust scene

APK 的 `libapp.so`、`libapp_launcher.so` 和系统 Flutter 引擎库均含 `.gnu_debugdata`。`libapp.so` 解压后的 ELF 符号表有 79,687 条命名文本符号。Dart snapshot 版本哈希为 `5d85d85296400e9b3992193deed317c9`，特征串显示 product、ARM64 Android 和压缩指针。版本哈希用于标识该快照，没有据此指定 SDK 版本。

| 已定位路径 | 调用和边界 |
| --- | --- |
| Dart `main` 到根视图 | `0x12d0c18 → 0x1adb9e8`，`0x1adba4c → _startApp 0x1ad83d8`。初始化闭包先调用 `HyperUIPlugin.init`，再经 `0x1ad8d74 → LauncherAddonManager.setInitialRoute 0x12cf3f0`，由 `0x12cf45c → AppEntrypoint.fromRoute 0x12cf4cc` 选择入口。`fromRoute` 的循环上限为 20（`0x12cf540`），在 `0x12cf570` 按字符串比较。启动闭包随后在 `0x1ad8f28 → runMultiWindowApp 0x12ce770` 进入根视图流程。D10 的 PID 6516 记录了 `initialRoute: /home`（`live-logcat.txt:83258`）。 |
| Rust 创建 scene 的正对照 | `recents_activity_ui::create 0x9250c8` 在 `0x92520c–0x925210` 取 `/recentsActivity`，并在 `0x92531c → engine_platform::embedding::scene::create<LauncherUi> 0x5c0444` 构造 scene。主屏和最近任务工厂都能到达该构造函数。`EngineGroup::create_and_run_engine 0xb9d430` 用 Flutter 表 `+0x40` 创建 shell holder 或用 `+0x50` 派生 shell，冷启动路径在 `0xb9e0c0` 调表 `+0x58` 的 `shell_holder_launch`（引擎 `0x6e808c`）。引擎接口可携带 Dart entrypoint、library、初始路由和启动参数。 |
| 次屏 HOME 类分派 | Rust `PlatformApplication<App>::request_ui` 中，`0x94e434–0x94e448` 比对次屏类名，命中后返回固定活动描述符 `0xe1d318`。`SecondaryDisplayLauncherUi::request_window 0x776834` 和 `on_create 0x776854` 都没有调用上述 scene 工厂或写入路由。窗口表 `0xe1e1f8` 的 created 槽 `0xe1e218 → 0x77a110` 仍释放传入引用；该函数地址在迷你符号表上也有 `NavBarStubView` 名称，次屏槽归属由重定位确定。 |

`_MultiWindowRootState.build 0x10ed2dc` 在 `0x10ed484` 包装默认视图，其他视图按已注册的 Flutter view ID 取 widget，缺少 widget 的分支在 `0x10ed58c` 跳过。这里使用 Flutter 的 view ID。要落到 Android Display 2，还需要在原生侧找到该 display 上的窗口与运行上下文。

## [ROM] 多视图窗口从哪里取得 Display ID

1. **Dart 到 Rust。** `RecentsWindowOverlay.showRecentWindow` 和 `GlobalHotseatWindowManager.createHotseatWindow` 分别在 `0x199e3fc`、`0x1b7c3d0` 调用 `MultiViewManager.addViewLight 0x199e550`。该方法通过 `flutter/platform` 提交 `MultiView.addLight` 和 `layout`。Rust `PlatformMethodHandler` 在 `0xa8e014–0xa8e03c` 比对该方法名，在 `0xa8f2e0` 解析布局并经虚表槽 `0xe89ee0 → PlatformHandler.add_overlay_view_light 0xa6ef1c` 分派。
2. **Rust 到系统窗口。** 该路径从当前 scene 读取 `WindowContext`、设备像素比和 looper（`0xa6f2c8–0xa6f348`），进入 `OverlayViewLight.add_window_impl 0xa65a00`。按窗口 type 与 1999 的比较，`0xa65e10` 调 `WindowManager_add_window`，或在 `0xa65e2c–0xa65e3c` 取 scene 的 `WindowOperation` 调 `WindowOperation_create_sub_window`。普通 `OverlayView` 也有这两类调用（`0xa674a0`、`0xa674cc`）。子窗口私有实现在 `0x1b8b34–0x1b8b38` 取父窗口 token 和该父控制器关联的 Runtime。两个路径都到 `0x1b3a20`，在 `0x1b3a54` 读 `Context.display_id`。运行库另有显式指定显示的 `WindowManager_add_window_for_display`（public `0x6f714`，private `0x1f609c`）；在核对的桥接调用中没有使用它。桥接路径的落屏结果依赖传入的上下文，不能从 Flutter view ID 推出。
3. **系统窗口到 Flutter。** 轻量窗口的 created 回调在 `0xa537fc → FlutterWindowState.on_created 0xb9bfb8` 绑定 `NativeWindow`；指标在 `0xa53c1c → 0xb9ce60` 进入已运行的 `GroupedEngine`。主屏的 `0x7780f8` 也调用 `0xb9ce60`。按窗口更新的分支在 `0xb9cb6c` 调 Flutter 表 `+0x190`，对应引擎 `shell_holder_set_window_viewport_metrics 0x6f0354`。D10 的次屏窗口配置有 `displayId=2` 和 `densityDpi=150`（`live-logcat.txt:38226,38563`），但次屏的 attached、created 与 metrics 槽没有保留这些对象或关联 `GroupedEngine`。运行库已将窗口和配置派发到次屏回调，现有回调没有把它们接给该桥。[次屏回调表与首帧对照](19-secondary-home-render-host.md)

## 已核对的其他入口

| 候选 | 可确认的用途或缺项 |
| --- | --- |
| `FoldCalculateHandler.calExternalScreen 0x1764c10` | [ROM] `0x1b9faec` 从 `FoldCalculateHandler.handle` 进入内外屏布局计算分支，调整 insets 和网格尺寸。已查函数没有 Android display 或 `NativeWindow` 输入。 |
| `LaptopWorkspace`、`LaptopCellScreen` | [ROM] `LaptopCellScreen.build 0x1535368` 构建网格和 `PageView`。当前只有 widget 构建证据，尚无窗口注册或次屏路由绑定。 |
| `MirrorDesktopBridgeApiImpl.performMirrorDeviceIconClick` | [ROM] `0x1401084` 经 Dart Rust bridge 调镜像设备图标操作，Rust 端对应 `0x8c04f0`。已查调用处理点击。 |
| `/desktop_setting` | [ROM] `libapp.so` 文件偏移 `0x3006b1` 存在该字符串，尚未恢复其 route 对象或确认哪个宿主会选择它。 |
| Display 2 的 taskbar | [ROM] `ILauncherProxy.onDisplayAddSystemDecorations` 在 `0x94d090` 调 `TaskbarManager.on_display_add_system_decorations`。[真机 D10] `MiuiTaskbarNavWindow_2` 在 Display 2，type 2019，token `12970367470982283616`，VRI 244（`live-logcat.txt:38820,38833,38934`）。次屏 HOME token 是 `12970367465612758864`，对应图层 232 和 273。这组窗口记录证明外屏 taskbar 有独立的窗口身份，无法据此认定次屏 HOME 已走 Dart 多视图。 |
| `secondary display present` 日志 | [ROM] Launcher 配置回调 `0x747498` 在 `0x7476a8` 取 `get_display_count`，数量大于 1 时跳过该分支的 relaunch-kill。计数来自 `DisplayManager.get_displays`，未按 `EXTERNAL` 筛选。[真机 D10] `live-logcat.txt:45710` 的实际计数为 3；日志定位到进程保留条件。 |

## 路线判断与验证条件

**[推测]** 阶段 2 和 3 保持 `PARTIAL`。现有证据支持复用 Flutter 的渲染和窗口桥，但两条路线仍共同缺少把次屏 HOME 的 activity token、`WindowOperation`、`NativeWindow` 和显示指标接到内容 scene 的调用边。已定位的原厂入口不足以直接选 A 或 B。下一项离线工作可沿主屏和最近任务的 scene 工厂核对最小可复用单元及其依赖，明确次屏独立的窗口和模型归属，并确认 attach、重建和拔线清理。应用图标启动的调用来源与目标任务归属仍待定位。

**[待真机]** 本轮 `NOT_RUN`。找到可复用的次屏入口或形成可单独验证的最小设计后，再按授权安排真机对照。沿 D10 的组 0、外屏 ON 条件，以同一 HOME token 关联 Flutter scene/view、`NativeWindow`、首个 buffer 入队与 latch、首帧通知及 WMS 完成。回切、拔线时重新核对图层 ID，并验证内屏和背屏仍按基线工作。

## 复查方法与范围

复用 `analysis/local/inputs/MiuiHome.apk`、Launcher 库副本和原 `system_ext` 提取目录。Python 3.14 用 `ZipFile` 读取 AOT 成员，用 `lzma` 解压三个 ELF 的 `.gnu_debugdata`。在 NDK 30.0.15729638（LLVM 21.0.0）用 `llvm-nm --demangle --numeric-sort --print-size` 给迷你 ELF 的函数定位。迷你 ELF 的 `.text` 是 `NOBITS`，指令从原库取。Dart AOT 的 snapshot 指令导出为 `OBJECT`，用 `llvm-objdump -D -j .text --start-address=<VA> --stop-address=<VA>` 解码。Rust 或引擎遇到 LLVM 无法识别的厂商区段时，沿报告 19 的原 `.text` 切片方法复查。用 `python scripts/verify_native_desktop.py --local --d10` 校验 APK 成员与原库哈希、迷你符号、字符串位置、直接分支、重定位和 D10 锚点。

原始 AOT 中搜索了 secondary、second、external、extended、wired、projected、projection 与 display、screen、home、desktop、workspace、launcher 的相邻组合（最多四个空格、下划线、点、斜杠或连字符），没有匹配到连续字符串。再用迷你符号表追查上表的同名或近似功能，按启动工厂、窗口调用和归档日志收窄。完整 Dart 对象池、20 个路由的名称及间接或动态注册路径未恢复。结论仅覆盖此版 ROM 的已核对入口。原库、符号全表及完整反汇编保留在 `analysis/local/aot-secondary/`。
