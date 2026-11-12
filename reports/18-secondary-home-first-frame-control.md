# 18 次屏 HOME 与计算器的首帧对照

2026-11-11（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`。按[报告 17](17-external-desktop-power-and-composition-control.md)的下一步，复用已停用的单资源 D3 Overlay。D10 接入镜像后保持同一条外屏连接，只将镜像值切到 `0`。两次采样均在同一个启动周期，Display 2 仍在组 0，外屏请求为 `BRIGHT`、物理 `ON/ON`、layer stack 2。内屏和背屏的电源策略未调整。

## 真机对照

| 测试对象 | WindowManager | SurfaceFlinger / HWC | 外屏物理截图 |
| --- | --- | --- | --- |
| `com.miui.home/.launcher.SecondaryDisplayLauncher` | HOME task 在 Display 2 resumed，窗口有 Surface、`shown=true`、`HAS_DRAWN` | SF 层树中可找到 VRI 图层 232，快照标为 `invisible reason=nothing to draw`。该物理外屏的 HWC 合成表只有状态栏 | 2560×1440，1,127 个非黑像素，全部在顶部第 16–33 行，中央区域全黑 |
| `com.miui.calculator/.cal.CalculatorActivity` | `am start -W` 返回 `Status: ok`，计算器 fullscreen task 在 Display 2，窗口 `shown=true`、`HAS_DRAWN` | VRI 图层 265 有 buffer，SF 记录 frame 6，HWC 合成表同时有计算器和状态栏 | 2560×1440，计算器实际内容出现在中央，1,698,628 个非黑像素 |

用户现场确认计算器出现在外屏中央。Task 的 `mode=fullscreen`，Activity 同时记录 `letterboxReason=FIXED_ORIENTATION`、`fixedOrientationLetterboxAspectRatio=1.22` 和水平位置系数 `0.5`。HWC 将 1180×1440 的应用图层放在 `(690,0)–(1870,1440)`，外屏本身仍输出 2560×1440 @ 60 Hz。证据见 `calculator-tasks.txt:3,52–69` 和 `calculator-sf.txt:1092–1102`。其他应用适配和桌面窗口交互仍待验证。

计算器启动前无已有进程或 Activity，测试后仅停止本次启动的计算器。退出后立即采的 HOME 回切截图与计算器截图 SHA-256 相同，当时还在过渡中，后续 HWC dump 已只剩状态栏。回切截图仅保留为时序记录。

## 次屏 HOME 的绘制同步

| 时间（北京时间） | 同一 HOME 窗口的事件 |
| --- | --- |
| 18:31:28.176 | 次屏 `on_create`、`on_start`、`on_resume`，MiuiHome 记录 `SecondaryDisplayLauncherUi::on_create` |
| 18:31:28.190–28.193 | WMS 绑定 VRI 图层 232，运行库创建 2560×1440 的 BLAST Surface，触发 `surface_created`、`surface_changed` 并开始等待绘制同步 |
| 18:31:29.270 | 次屏 token 的 `wmssync mark_sync_ready reason=timeout`，`finishDrawing` 记录 `has_tx=false`、`render_target_valid=true`、`sc_valid=true`、`window_stopped=false` |
| 18:31:29.274–29.294 | WMS 收到 `finishDrawing`，随后记录 show；SF 抓屏将同一个 VRI 图层记为 `invisibleChildLayer` |

该次对照将持续黑底定位到次屏 HOME 的可绘制内容。状态栏和普通 Activity 均能通过同一外屏合成链。WM 的 `HAS_DRAWN` 在此与超时后的完成通知对应，SF 快照中该 HOME 图层仍无可绘制内容。现有记录未定位 Launcher 是在哪个入口没有交付首帧，也未证明同步超时本身导致缺帧。

[ROM] 已知次屏窗口的 `on_surface_created` 槽走指标向量析构并释放传入对象。它提供了一个可对照的入口。[窗口回调与实参](12-native-secondary-home-display-routing.md)

[ROM] 后续离线对照已定位主屏 Flutter 的窗口绑定入口、次屏回调缺口及超时无事务路径。D10 回切后同一 HOME token 换用新图层，仍无可绘制内容。[报告 19](19-secondary-home-render-host.md)

## 回退与证据

两次重启分别用于启用和停用 D3。停用后测试模块保留，挂载 APK、测试包和 Overlay 条目均退出，三项资格回到 false，其余 8 个模块状态与启用前相同。镜像值恢复为 1。无线调试原值为 1，重启后经有线恢复，最后从设备返回的 TLS 端口重新接入。用户确认镜像正常，复核外屏位于组 0、物理 ON、SF 活动模式为 2560×1440 @ 60 Hz。

原始数据在 `analysis/local/device-validation/*-D10-desktop-content-control/`。主要锚点为 `home-windows.txt:125–157`、`home-sf.txt:632–635`、`calculator-sf.txt:399–402,1092–1102`、两张 `*-physical.png`，以及 `live-logcat.txt:38225,38473,38511–38546,39332–39357,39466`。回退的画面和物理模式见 `rollback-live-*`，原始日志与截图留在本地。
