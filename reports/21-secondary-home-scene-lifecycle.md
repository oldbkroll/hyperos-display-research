# 21 次屏 HOME 可复用的 scene 与窗口生命周期

2026-11-12（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`，从 `2622c40` 续查。复用同版 ROM 和已归档的 D10。新增真机验证为 `NOT_RUN`。[ELF 和 AOT 锚点](../analysis/evidence/native-secondary-aot.json) · [D10 日志锚点](../analysis/evidence/native-first-frame.json)

**[ROM] 原厂 Flutter 的 scene 和窗口生命周期可由不同业务类使用。`LauncherUi` 有写入进程级窗口引用的路径。** 主屏和最近任务共用该业务类与 scene 工厂。`SettingsUi` 使用另一业务类，也能走同一套 `GroupedEngine` 与 `SceneDelegate`，为独立 scene 提供了静态对照。阶段 2/3 保持 `PARTIAL`。已定位渲染接入和释放边界，次屏内容入口、桌面模型和应用落屏仍需落实。[前一轮 AOT 入口分析](20-secondary-home-aot-entry.md)

## [ROM] 通用 scene 与 Launcher 业务分界

| 路径 | 已确认的依赖 |
| --- | --- |
| 主屏 HOME | `request_ui` 在 `0x94e4cc → LauncherUi::new 0x7b8ae8` 构造业务对象，再于 `0x94e4e0 → scene::create<LauncherUi> 0x5c0444` 构造 scene。`0x5c058c` 创建 `SceneDelegate`，`0x5c0638/0x5c0640` 创建持有引擎的 `OnceCell`，`0x5c06dc` 建立引擎配置。工厂后续还注册 heap、gfx、mem 等诊断回调。 |
| 最近任务 | `0x94e4a0 → recents_activity_ui::create 0x9250c8`。工厂在 `0x925170` 把 token 写进 `EngineSnapshot`，`set_token 0x6b97c4` 原子替换该字段。工厂设置 `/recentsActivity` 与 `--activity_name=`、`--uuid=` 参数，仍在 `0x925300` 创建 `LauncherUi`，于 `0x92531c` 进入相同 scene 工厂。它还在 `0x925318` 设置专用标志，与 `LauncherUi` 销毁时 `0x7623f8–0x762404` 的 snapshot 清理分支相对应。这个例子证明另一个 Activity 可启动自己的场景，也包含最近任务自身的进程级协作。 |
| `SettingsUi` | 活动表槽 `0xe1c560 → on_create 0x768754`。它在 `0x768810` 创建引擎，`0x768924` 调 `SceneDelegate::pre_on_create`，`0x7693a4` 调 `post_on_create`，期间在 `0x768b00` 创建自己的 `AppInterfaceImpl` 并注册插件。对应主屏的通用调用在 `0x76612c`、`0x766240`、`0x766294`，主屏业务调用是中间的 `0x766270 → LauncherUi::on_create`。因此 scene 可以选用不同业务类和插件。 |

`GroupedEngine` 可以走同一引擎组派生新的 shell，原生 `EngineGroup::create_and_run_engine` 在 `0xb9d74c–0xb9d758` 从组内取得已有 holder，并在 `0xb9d7e8` 调 spawn。已有 holder 可供派生，与把两个窗口绑到同一个 holder 是不同的所有权关系。空组仍可走冷启动。工厂的包装类型、`Arc` 持有关系、路由和回调必须配套，单独调用一个固定地址不足以建立 scene。

**进程级状态的证据。** `LauncherUi::on_create` 的 `0x971044` 读取自己的 `SceneContext.window_operation`，`0x971054` 写入 `GlobalStates::set_window_operation`。主屏窗口的 attached 回调另在 `0x777b40` 写同一个位置。setter 在 `0x6a9be0–0x6a9be4` 读取并替换 `0xf22408` 的单个引用，随后释放旧引用，接口没有 display 或 token 键。Dart `_LauncherAppState.initState` 还在 `0x1468b88/0x1468bb0/0x1468bb4` 注册最近任务清理、离线 widget receiver 并初始化最近任务与手势；`dispose` 会注销两个 receiver。第二个 shell 的内容是否能复用 `/home`，仍需验证这些注册的作用域和桌面模型的写入归属。

## [ROM] 首帧、Surface 重建和 scene 销毁

| 生命周期 | 可复用部分与所有权 |
| --- | --- |
| 创建与绑定 | 通用 `pre_on_create` 读取 `UiComponentData` token 和配置并初始化 scene 状态。主屏 `0x766190–0x7661a0` 另将显示属性送给本 scene 的引擎。窗口描述符在 `0x763c20` 创建 `WindowDelegate`，attached 在 `0x777b04` 进入通用委托，保留 `WindowOperation` 并在 `0xa5f3c0` 取窗口 token。created 在 `0x7776e0` 绑定 `NativeWindow`；surface size 与 viewport metrics 随其窗口进入引擎。活动 token、窗口 token、Flutter view ID 分别取自各自接口。 |
| 首帧完成 | `PlatformCallbacksDelegate` 的默认窗口回调 `0xf06570 → 0xd447a0` 从本 scene 的已初始化 `WindowOperation` 读取引用，并在 `0xd447cc` 通知 `first_frame_call`。按窗口 ID 的回调 `0xf065a0 → 0xd44930` 则先在 `0xd44998` 按 ID 查本 scene 的 overlay view，命中后才在 `0xd44a20` 通知对应窗口。若采用独立 scene 的根窗口，应满足默认回调的绑定条件；若采用额外 view，则需要对应登记。Surface 的 buffer 入队和 latch 仍要独立观察。 |
| Surface 销毁与再建 | 主屏槽 `0xe1d6a8 → 0x777990` 在 `0x7779a4` 调 `FlutterWindowState::on_destroyed`，再于 `0x777a20` 调 `WindowDelegate::on_destroyed`。Flutter 端由 `0xb9cd84` 调表 `+0x188` 的逐窗口销毁（`0x6efe0c`），或由 `0xb9cdc4` 调 `+0xc0` 的根 Surface 销毁（`0x6ea5d0`）。这层处理旧 Surface，scene 仍可接收该窗口的新 Surface。 |
| 窗口 detached 与 scene 销毁 | `0xe1d6c0 → 0x77801c` 在 `0x7780a8` 调 `WindowDelegate::on_detached`，包含颜色和无障碍相关清理。活动槽 `0xe1c478 → 0x762204` 在 `0x763234–0x76324c` 移除多视图管理器、调用 `SceneDelegate::on_destroy` 并关闭 messenger。引擎从组内移除和释放由 `GroupedEngine` 的引用计数管理，最后一个 `GroupedEngineInner` 释放时，`0xb9d180` 调 Flutter 表 `+0x48 → shell_holder_destroy 0x6e7e90`。 |

**D10 对照。** 计算器前台时，`live-logcat.txt:41908–41914` 记录次屏 HOME `on_stop`，随后销毁 VRI 232 的 Surface。回切后在 `44159–44203` 用相同活动 token `12970367465612758864`、相同 WM 窗口 `3f30d8e` 建立 VRI 273。拔线时 `45625` 记录 Display 2 从拓扑移除；`45725–45732` 先销毁 Surface，随后 `on_destroy`、移除活动 token 并请求移除窗口。切到应用再回桌面与拔线是两个不同的清理层级。D10 的次屏仍是原厂空回调，日志只提供系统生命周期顺序。[D10 首帧对照](18-secondary-home-first-frame-control.md)

## [推测] 最小接入设计与剩余准入条件

先保留 `SecondaryDisplayLauncher` 的 Activity 和系统分配的窗口，在 MiuiHome 内给该 Activity 一个独立 scene。可复用 `SceneDelegate`、引擎组和 `FlutterWindowState`；首个验证版本只需一个可达、能提交可辨认帧的 Dart 根视图。次屏 scene 只接受自身窗口的 `WindowOperation`、`NativeWindow` 和 viewport，按当前 Surface 身份配对回调。次屏 HOME 不应调用会覆盖 `GlobalStates` 主窗口引用的 Launcher 业务路径，也不应占用最近任务的 `EngineSnapshot` token。这个设计仍需找到或实现可进入的 Dart 根视图，当前 ROM 未确认可直接用的次屏内容入口。

1. `on_create` 建立 Activity 级 scene，并从该 Activity 配置初始化显示属性。attached 后将该 scene 与运行库给出的窗口对象关联。绑定当前 Surface 并应用该窗口最新的 viewport。原厂默认首帧回调没有 Surface 代次参数，需要核对重建后如何重新注册，以及如何排除上一代 Surface 的迟到通知。
2. `on_surface_destroyed` 使旧 Surface 对应的异步绘制结果失效，释放其渲染目标。Activity 和窗口仍有效时允许重建，重新绑定和确认首帧。最终退出时按 scene/窗口归属注销监听、释放 `WindowOperation` 和引擎引用。清理需要容忍 Surface 先销毁、晚到回调和重复退出通知。
3. 在恢复完整桌面前，另行核对 `/home` 的模型和手势注册能否按 scene 隔离，并查清点击图标的来源 token、目标 display 和任务复用规则。应用落屏链仍待查。路线 A/B 的窗口管理准入以这部分证据为前提。[应用落屏已有证据](12-native-secondary-home-display-routing.md) · [两条路线的准入条件](09-native-desktop-minimal-design.md)

**[待真机]** `NOT_RUN`。在有可审查的首帧实现并另行获得设备授权后，用 D10 的组 0、外屏 ON 条件验证两次绑定和一次最终释放。初建和回切分别按当前 layer ID 核对 buffer 入队、latch 和实际画面，拔线后确认次屏 scene 与窗口已释放，内屏和背屏仍按基线工作。

## 复查方法

复用报告 20 的 APK、原 `system_ext` 和 ELF 迷你符号。用同一 NDK LLVM 对 `0x5c0444`、`0x9250c8`、`0x766074`、`0x768754`、`0xb9cd20` 和 `0xb9d150` 定向反汇编，以 Launcher 的 RELA 和 Flutter 的 RELR 对齐两个首帧槽与三个释放槽。`python scripts/verify_native_desktop.py --local --d10` 校验新增调用边、符号、重定位和 D10 原始日志行。
