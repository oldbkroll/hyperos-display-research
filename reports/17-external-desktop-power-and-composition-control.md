# 17 外屏共组、电源恢复与状态栏对照

2026-11-11（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`。D9 使用[报告 15](15-device-desktop-qualification-preflight.md)的原单资源 Overlay，执行[报告 16](16-external-desktop-power-group.md)的同一次启动对照。用户授权操作并要求优先停用模块。外屏插拔和现场画面由用户确认。共重启两次，分别用于生效和停用回退。

## 同一次启动的证据

| 状态 | 显示组与电源 | 内容与现场结果 |
| --- | --- | --- |
| Overlay 已启用，镜像值 `1` | 内屏和外屏在组 0，外屏 `BRIGHT/UNKNOWN`、物理 `ON/ON`，背屏单独在组 1，`DOZE/OFF` | 用户确认镜像有画面 |
| 同一连接将镜像值写为 `0` | 连续三个快照仍是组 0，外屏物理 `ON/ON`、layer stack 2 | `canHostTasks=true`，`SecondaryDisplayLauncher` 在 Display 2 resumed。缺该时段的物理截图 |
| 重插外屏，等待确认连接 | 日志显示外屏先分组 0，再进入组 1。背屏与外屏都收到 `DOZE/OFF`。外屏逻辑 `mIsEnabled=false`，物理 `OFF/OFF`、layer stack `-1` | 该快照处于待启用窗口。禁用状态和 DOZE/OFF 各自都能让 DPC 选择 OFF |
| 连接确认后，镜像仍为 `0` | 外屏逻辑启用，HWC 回到 ON，物理 layer stack 重新绑定 2 | 用户看到黑底和状态栏。2560×1440 物理截图有 1,131 个非黑像素，全部位于顶部第 16–33 行。SF 抓屏记录将次屏 Launcher 的 VRI 子图层标为 `invisibleChildLayer` |
| 写回镜像值 `1` | 外屏仍与背屏共组，两者 DPC 请求仍为 `DOZE/OFF`。外屏 DPC 的 `mScreenState=OFF`，物理状态却为 `ON/ON`、layer stack 2 | 用户看到画面恢复镜像。组 1 共组时写回镜像可以恢复画面，组号仍待重新分配 |

重插前后，PMS 组 1 始终为 Dozing，`mWakeLockSummary=0x40`、最后一次唤醒与休眠原因一致。用各快照的 uptime 和 `dream:doze:1` 已持有时长反算，唤醒锁约在开机后 29.0 秒取得，前后时间一致。组 1 已有的 DOZE/OFF 策略被新成员复用。接入时的物理 OFF 同时发生在外屏等待启用期间，现有对照无法独立测量两个条件各自造成的影响。

### 事件顺序

以下是同一设备的日志时间（北京时间）。

| 时间 | 事件 |
| --- | --- |
| 18:16:12.906 | 镜像阶段的 Dream 请求 `OFF`，PMS 记录 `setRearDozeState: newScreenState=1`。随后镜像快照中背屏保持 `DOZE/OFF` |
| 18:16:43.174 | DMS 更新镜像为 false，Display 2 可承载任务。外屏仍在组 0 |
| 18:17:10.263–10.278 | 重插后 Display 2 设为 disabled。18:17:10.275 从组 0 进入组 1，`reason=1`、flags 为 0，随后 LocalDisplayAdapter 与 HWC 记录 OFF |
| 18:17:19.514–19.573 | Mapper 将 Display 2 设为 enabled，LocalDisplayAdapter 与 HWC 记录 ON，ATMS 启动次屏 HOME，SF 将该物理外屏的 layer stack 设为 2 |
| 18:17:19.612–20.681 | WM 显示外屏状态栏。随后的物理抓屏中 SF 记录次屏 Launcher 的 VRI 子图层不可见 |
| 18:17:34.361 | DMS 收到本轮写回的镜像值 `1`。写回之后才出现用户看到的镜像恢复 |

重插加入组 1 到启用约 9.24 秒。日志这段期间未见组 1 唤醒或新的 Dream 状态写入。现场的「黑底、可见状态栏」对应外屏已 ON 的阶段，独立桌面内容仍未通过验收。

## [ROM] 组策略与外屏启用各有入口

- `ConnectingDisplayViewModel.applyConnectionChoice()` 可经 `enableConnectedDisplay()` 请求启用外屏。DMS 对 EXTERNAL 仍走 `ExternalDisplayPolicy.setExternalDisplayEnabledLocked()` 的外屏允许条件，再进入 `LogicalDisplayMapper.setDisplayEnabledLocked()`。D9 运行时见到 `SetEnabled on display 2: true`，未单独记录这次 Binder 调用的调用者。
- Mapper 对已连接且从 disabled 变为 enabled 的逻辑屏可发出 ADDED。DMS 的 `handleLogicalDisplayAddedPreProcessLocked()` 将该显示的缓存状态设为 ON，后处理经 `updateLogicalDisplayState()` → `updateDisplayStateLocked()` → `DisplayDevice.requestDisplayStateLocked()` 下发。这个入口可解释日志中外屏物理 ON 早于次屏 HOME 启动，且同组 DPC 请求仍为 DOZE/OFF。两个状态分别来自 DMS 物理状态下发与 PMS 组策略。
- 证据锚点位于 `analysis/local/jadx/services/sources/com/android/server/display/` 的 `DisplayManagerService.java:2711–2717,2749–2764,2904–2914,4167–4180,4578–4627`、`LogicalDisplayMapper.java:725–736,1317–1324`、`ExternalDisplayPolicy.java:109–122`，以及 `analysis/local/jadx/systemui/sources/com/android/systemui/display/ui/viewmodel/ConnectingDisplayViewModel.java:226–258`。

D9 没有启动额外测试 Activity。D10 已利用「已连接、仍在组 0、关闭镜像」的窗口完成 HOME 与计算器对照，确认前者无可绘制内容、后者进入物理合成。[报告 18](18-secondary-home-first-frame-control.md)

## 停用回退

安装前有线和无线 ADB 指向同一启动，有线 root、`hybrid_mount`、ROM 版本和候选 APK 哈希均复核通过。检测到上轮 15:10 遗留的空 `/cache/.disable_magisk`，其时间早于上轮 Overlay 成功加载。保留该文件，`RescueBrick/.enable_apps` 与 `activate` 在本轮前后均缺席。两次重启均由有线 ADB 发起。无线调试重启后回到 `0`，两次都用有线 root 恢复原值 `1` 并核对无线 ADB 接回。

用 `ksud module disable displayresearch_d3_qualification` 停用 D3，重启后模块保留且 `enabled=false`、`remove=false`、`update=false`。挂载的 APK、包管理中的测试包和 Overlay 条目均消失，三项资格恢复为 false，Android Overlay 列表和原有 8 个模块状态与基线一致。用户重新接外屏并确认镜像正常。无线复核确认内屏与外屏在组 0、背屏单独在组 1，外屏 `BRIGHT`、物理 `ON/ON`、SF 为 2560×1440 @ 60 Hz。

原始证据保存在 `analysis/local/device-validation/*-D9-desktop-power-control/`。主要锚点为 `active-mirror-*`、`pre-switch-*`、`switch-stable-*`、`replug-2-1-*`、`replug-physical.png`、`restore-before-unplug-*` 与 `rollback-mirror-live-*`。事件见 `live-logcat.txt:8036–8042,19927–19928,30410–30522,33895–35070,35758,36098,38092–38093`。原始日志和截图留在本地。
