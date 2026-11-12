# 22 原厂首帧对照入口与 Surface 重建回调

2026-11-12（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`，从 `e5717c7` 续查。使用同版 ROM 和 D10 归档，新增真机验证为 `NOT_RUN`。[AOT、Rust 和引擎锚点](../analysis/evidence/native-secondary-aot.json) · [D10 归档锚点](../analysis/evidence/native-first-frame.json)

**[ROM] 应用分类设置页有可达的原厂 Dart entrypoint，可作为独立 Flutter scene 的首帧正对照候选。** 原厂根 Surface 创建路径会重新安装下一帧回调。回调检查平台视图的弱引用，但携带的参数没有 Surface 身份；窗口销毁等待渲染目标释放，尚无证据表明它会撤销已投递的平台线程回调。次屏 HOME 的独立 scene 仍需一个自己的内容入口和可归属到当前 Surface 的首帧通知。[独立 scene 条件设计](21-secondary-home-scene-lifecycle.md)

## [ROM] 应用分类设置页的启动链

1. **Activity。** 用 `aapt2 37.0.0` 复核 MiuiHome APK 的 manifest，`com.miui.home.launcher.allapps.settings.CategorySettingActivity` 声明 `exported=true`、`launchMode=1`（singleTop）、`screenOrientation=1`（portrait）。Rust `request_ui` 在 `0x94ddf0–0x94de00` 比较该类名，经 `0x94f338 → all_apps_settings_ui::create 0x92536c` 创建场景。
2. **原厂 Dart entrypoint。** 工厂在 `0x925400–0x925408` 再按类名匹配，在 `0x92541c–0x925420` 选择 `categorySettingsPage`，经 `0x9254cc → SceneConfiguration::with_user_args` 将名称放入引擎配置，同时保留 `--activity_name=` 和 `--uuid=`。工厂将 entrypoint 写进配置，初始路由沿用默认值；`/category_setting` 的字符串是独立锚点。Dart 的 `categorySettingsPage` 在 `0x12d0020 → 0x1ad835c` 进入函数体，`0x1ad83cc → _startApp 0x1ad83d8`。入口从对象池取得自身的启动配置，沿公用 `HyperUIPlugin.init` 和 `runMultiWindowApp` 流程。`CategorySettingsPage.build 0x153ff18` 使用 `Theme`、`AppLocalizations`、`MediaQuery` 及 `settingsSystemUiRegion`，有可辨认的内容；完整对象池中的 widget 构造链未恢复。
3. **实际渲染宿主。** 活动槽 `0xe1cde0 → 0x7738b0` 在 `0x77396c` 创建引擎，`0x773a80` 和 `0x774500` 调 scene 的前后创建回调。它在 `0x773c48` 获取本 scene 的 `WindowOperation`，为 `AppInterfaceImpl` 和插件提供上下文。窗口表 `0xe1dcf0` 的 created 槽 `0xe1dd10 → 0x779df0` 在 `0x779e2c` 调通用 `FlutterWindowState::on_created`。这条链具备和主屏相同的引擎及 Surface 绑定基础，页面仍依赖应用插件和设置服务。

抽屉背景设置页也有完整的命名入口 `drawerBackgroundSettingsPage`，走同一 Rust 工厂的另一类名分支。手势演示完成页有 `demoFinishPage`，但其状态恢复路径在 `0x1b29b68` 可调用 `Settings.putInt`，不适合作为只观察画面的首个对照。`/recentsWindowPlaceholder` 在 AOT 中有字符串，尚未定位可直接从独立 scene 启动的入口，也没有可辨认画面的证据。优先保留分类设置页作为完整 Activity 的正对照候选。它采用竖屏方向，外屏实验应接受 letterbox，并记录实际落屏，不从 manifest 推断 WMS 会允许启动到外屏。

## [ROM] 从 Surface 创建到首帧通知

| 阶段 | 控制流与身份 |
| --- | --- |
| 随根 Surface 创建注册 | Flutter 表 `+0xa8 → shell_holder_surface_created 0x6ea52c` 在 `0x6ea5bc` 调 `hyper_SurfaceCreated 0x6f2e14`，逐窗口入口也有回到该根窗口处理的分支（`0x6ee9d4`）。`hyper_SurfaceCreated` 在平台视图已有渲染目标对象的分支中，于 `0x6f2f5c–0x6f2f88` 构造 `InstallFirstFrameCallback` 闭包并调用 Shell `OnPlatformViewSetNextFrameCallback`，虚表槽 `0x11a0388 → 0xe4ea54`。这是创建路径上的注册，同一个 shell 的根 Surface 销毁后再建也会重新走该入口。 |
| 渲染线程消费 | Shell 的注册闭包（`0x11a16d0 → 0xe5e7ac`）向 `Rasterizer` 的待执行回调向量追加一个闭包。`DrawToSurfacesUnsafe` 在 `0xe392fc` 记录 raster end，随后在 `0xe39304–0xe39434` 取走回调向量、清空原字段并逐个执行。该回调与当前渲染轮次关联，实际 buffer 入队、latch 和外屏画面仍需另采。 |
| 投递给平台线程 | 安装闭包的调用槽 `0x1166bb8 → 0x700e54` 构造新闭包并在 `0x700ec0` 调 task runner `PostTask`。平台闭包 `0x1166c00 → 0x701094` 检查捕获的弱引用仍有效，在 `0x7010bc` 走平台通知，并在 `0x7010cc` 用 view ID `0` 调 `DispatchFirstFrameToDart`。该闭包没有捕获 `NativeWindow`、BLAST 队列 ID 或 Surface 代次。 |
| 释放时的边界 | 根 Surface 销毁 `0x6ea648 → PlatformViewAndroid::NotifyDestroyed 0x6ff008`，经 Shell 槽 `0x11a0358 → OnPlatformViewDestroyed`。Shell 的 raster task 在 `0xe60814` 以 view ID `0` 调 `UnregisterViewSurface`，销毁链等待任务完成（`0xe4dbe8`、`0x6ff184`）。该等待证明已同步释放渲染目标，已查路径中没有按 Surface 代次过滤或撤销已经排队的平台通知。 |

`WindowOperation.first_frame_call` 只收到 `WindowOperation`。私有实现 `0x1bb66c` 在 `0x1bb708` 从当前窗口状态取得 Surface，再于 `0x1bb720` 更新其 surface group。旧通知若在新 Surface 已绑定后到达，单靠活动 token 或窗口 token 无法判别其来源。D10 归档中计算器回切前后正是同一 HOME token、两个 Surface（VRI 232、273）。D10 `live-logcat.txt:79596` 的 `NotifyDestroyed() Done` 对应同进程主屏 Flutter 释放，与紧邻的 Launcher VRI 156 producer 断开相符。归档没有证明在次屏出现过旧回调误完成。[D10 生命周期](21-secondary-home-scene-lifecycle.md)

## [推测] 首帧验收与下一步

- **原厂正对照。** 另行授权后，可在已知外屏 ON、同一次物理连接条件下，采应用分类设置页启动、切走和回切。仅观察页面与窗口，记录实际 display、activity token、窗口、图层及 buffer 入队和 latch。若外屏落点或回切重建条件未满足，保留相应证据。该对照用于确认原厂 Flutter Activity 在目标输出链上的绘制，独立 HOME 仍依赖自己的绑定。
- **次屏 HOME 首帧设计。** 先用无桌面模型写入的可辨认根视图验证独立 scene。若同一 scene 保留并重绑根窗口，在创建或注册回调时捕获该次绑定的 Surface 身份。销毁时先令该次绑定失效，回调送给 `WindowOperation` 前核对捕获身份仍与当前绑定一致。读取回调到达时的当前身份只能确认当前窗口存在。若暂时只能使用不带身份的原厂回调，首帧验收以对应新图层的 buffer 和物理画面为准；完成通知的归属仍需解决。
- **阶段状态。** 阶段 2/3 保持 `PARTIAL`。原厂分类设置页的外屏落点和实际出帧为 `[待真机] NOT_RUN`。独立 HOME 的可达首帧内容、旧回调隔离和点击应用落屏仍待实现或验证。

复查用 NDK 30.0.15729638 LLVM 21.0.0 定向反汇编与迷你符号表，按 Launcher RELA、Flutter RELR 核对各回调槽。APK manifest 用 SDK 37.0.0 的 `aapt2 dump xmltree` 复查。`python scripts/verify_native_desktop.py --local --d10` 校验 APK、ROM 库、上述分支、重定位、字符串及归档行锚点。
