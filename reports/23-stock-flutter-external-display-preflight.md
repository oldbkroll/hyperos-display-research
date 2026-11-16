# 23 原厂 Flutter 外屏出帧与桌面模式变化

2026-11-12（北京时间），从 `main` 的 `c9a3b81` 接手。[报告 22](22-secondary-home-first-frame-entry.md)中的 `com.miui.home.launcher.allapps.settings.CategorySettingActivity → categorySettingsPage` 为原厂 Flutter 对照候选。16:23–16:24 先做有线 ADB 只读预检。同日获授权复用 D3、切换镜像并回退。复测确认分类页在外屏出帧，同时触发内屏切换到抽屉模式。内屏已恢复经典模式及原布局，外屏已恢复镜像。

## 真机基线

| 检查 | 起始与收尾采样 |
| --- | --- |
| 设备与 ADB | 有线 `adb -d` 已授权，状态 `device`。设备为 popsicle，HyperOS `OS4.0.6.0.XPBCNXM`，Android 17 / SDK 37，用户 0。两次采样处于同一启动周期。 |
| 外接显示 | `external_display_connected=0`。DMS 只列出两个 `INTERNAL`，SurfaceFlinger 也只枚举到对应的两块物理屏。无外屏逻辑 ID、组、电源或活动输出模式可采。 |
| 内屏 | Display 0，组 0，DPC 请求 `BRIGHT`，DMS 物理状态 `ON/ON`，SF `On`。 |
| 背屏 | Display 1，组 1，DPC 请求 `DOZE/OFF`，DMS 物理状态 `OFF/OFF`，SF `Off`。 |
| 镜像和资格 | secure `mirror_built_in_display=1`，DMS `mMirrorBuiltInDisplaySetting=true`。三个桌面资格资源均为 `false`，Android Overlay 列表无 D3 测试项。 |
| 前台和目标 | 内屏始终为系统设置 `SubSettings`，两次是同一 ActivityRecord。包管理器能解析分类设置页，两次任务快照都没有该 Activity。 |

D10 收尾的 1440p60 镜像是[历史实测](18-secondary-home-first-frame-control.md)。本轮未枚举到外屏，镜像设置值只反映策略配置，无法据此记录当前外屏画面或模式。

首次预检因无外屏停下。两次只读采样确认前台、显示组、电源及镜像设置一致。

## 同一连接的独立显示与息屏

有线 ADB 验证现存 D3 模块停用、内置 APK 与本地候选哈希一致，其他模块标记与 D10 回退记录一致。启用 D3 并重启后，只有 `config_isDesktopModeSupported` 变为 `true`。恢复无线调试并核对有线和无线 ADB 的 boot ID 一致，再由用户把唯一的 USB-C 口换接显示器。用户确认镜像正常。

| 时点 | Display 2 与外屏合成 |
| --- | --- |
| 接入并保留镜像 | `mirror_built_in_display=1`，组 0，物理 `ON/ON`，`canHostTasks=false`，SF 活动模式 2560×1440 @ 60 Hz。背屏单独在组 1。 |
| 同一连接临时关闭镜像 | 镜像值和 DMS 策略均切到关闭。外屏仍为组 0、物理 `ON/ON`、layer stack 2，`canHostTasks=true`，活动模式一致。内屏和外屏的 DPC 请求已是 `DIM`。 |
| 启动前复核 | 外屏迁到背屏的组 1，DPC 为 `DOZE/OFF`，物理 `OFF/OFF`。外屏仍有逻辑 ID 2，组 0 已唤醒，内屏物理 `ON/ON`。 |
| 写回镜像值 `1` | DMS 恢复镜像策略，`canHostTasks=false`。同一连接下外屏仍在组 1，DMS `OFF/OFF`，SF `Off`。 |

设备日志时序为 16:36:42.990 DMS 收到关闭镜像，16:36:56.046 PMS 记录因空闲超时息屏（`screenOffTimeout=120000`），16:36:56.048 组 0 进入 Dozing。16:36:56.098 Mapper 将 Display 2 从组 0 迁至组 1（`reason=1`，`flags=0`），紧接着 DMS 和 SF 各记录该物理外屏 `OFF`。16:36:58.432 组 0 已回到 Awake，外屏未随内屏恢复。用户报告现场有两次息屏。本段电源日志能确认上述一次空闲超时及随后的外屏关闭，第二次现场现象缺少可独立对应的电源或热插拔记录。

切到独立显示后约 13 秒进入 Dozing。独立状态初采和启动前复核相隔约 43 秒，采集准备占用了这段时间。下一轮应在切镜像前备好采集和启动命令，确认内屏明亮且保持唤醒后连续执行。

**第一次出帧对照 `NOT_RUN`。** 启动前复核触发共组和外屏 `OFF/OFF` 停止条件，未发送分类页启动请求。

## 第一次回退

写回镜像值后，经用户将显示器换回 USB 数据线，有线 ADB 停用 D3 并重启。复核 D3 保留且停用，其他模块标记、Overlay 列表及三个资格值与初始基线一致。两次重启后 `adb_wifi_enabled` 均回到 `0`，用有线 ADB 恢复到 `1`。两次均在读回 `1` 但无线监听端口未出现时，于用户解锁后重开一次无线调试，核对无线与有线 boot ID 一致。

回到续测前的内屏前台后，用户再次接入外屏并确认镜像画面正常。无线 ADB 复核 Display 2 在组 0、物理 `ON/ON`、`canHostTasks=false`，SF 活动模式为 2560×1440 @ 60 Hz。内屏在组 0、物理 `ON/ON`，背屏单独在组 1、物理 `OFF/OFF`。

## 复测与出帧证据

预先准备采集脚本，将系统息屏时间从 120 秒临时延至 600 秒。复用原 D3，重启后验证无线 ADB 和有线 ADB 同一启动。用户接入外屏并确认镜像。保持同一次连接关闭镜像，复核 Display 2 仍为组 0、物理 `ON/ON`、`canHostTasks=true`、layer stack 2，SF 活动模式为 2560×1440 @ 60 Hz，随后启动分类页一次。

| 环节 | 证据 |
| --- | --- |
| 实际落屏 | `am start -W` 返回 `ok`、`WARM`、`TotalTime: 77`。ActivityRecord 和聚焦窗口均归 Display 2，应用任务记录 `FIXED_ORIENTATION`。WMS 将该窗口绑定到 VRI `#262`。 |
| Flutter 首帧 | 16:48:25.323 进入 `categorySettingsPage`。16:48:25.346 为该 VRI 创建 1180×1440 的 BLAST Surface。16:48:25.371 rasterizer 记录首帧 `draw_status=0`、`has_content=1`，并触发 `first_frame` 绘制同步。 |
| 外屏实际合成 | 同一 VRI `#262` 在 SF 快照可见，持有 buffer 和 frame 6，出现在对应物理外屏的 HWC 图层表。物理抓屏为 2560×1440，用户确认实体屏幕上的分类设置内容正确。 |
| 入队、latch 和 present | 首次启动的 Perfetto 传输未生成可用 trace，首个 buffer 的入队与 latch 时刻未单独取得。切走时的 trace 记录同一 BLAST 队列 frame 34 的 `queueBuffer`、`onFrameAvailable`、`acquireNextBufferLocked`，以及 VRI `#262` 的 `latchBuffer`。同一帧的 Surface Frame token 在 FrameTimeline 对应 `On-time Present`。 |

**分类页外屏出帧 `PASS`。** 通过范围为原厂分类设置页的 Flutter 内容。独立次屏 HOME 保留 [D10 的结论](18-secondary-home-first-frame-control.md)。

## 切走和回切

用同一外屏上的临时计算器任务遮盖分类页。原分类 ActivityRecord 保留且为 `STOPPED`。16:50:42.118–42.136 记录根 Surface 销毁、`NotifyDestroyed()` 完成，以及原 VRI `#262` 的 BLAST producer 和 consumer 断开。普通 shell 的外屏 Back 被 `INJECT_EVENTS` 权限拒绝。准备通过移除本次计算器任务回切时，16:51:23.708 再次观察到外屏从组 0 迁到背屏组 1，DMS 和 SF 紧接着下发 `OFF`。当时系统息屏值仍是 600 秒，组 0 的收尾快照为 Awake，这次迁组的触发源尚未定位。

**[待真机] 回切 `NOT_RUN`。** 共组并关闭后停止。已确认切走时旧 Surface 销毁，回切时是否创建新 Surface 及新图层是否出帧仍待验。

## 内屏副作用和最终恢复

16:48:25.343，分类页启动阶段的 MiuiHome 日志记录 `change_launcher_mode: old: "desktop" new: "drawer"`。随后切到独立的抽屉模式布局数据库，并清空内存中的桌面工作区。期间只启动和观察分类页。用户看到内屏先只剩壁纸，切到计算器后发现桌面变为抽屉模式。该入口会改变主屏桌面模式，后续只读对照应避开这个入口。触发共享状态写入的具体代码路径仍待定位。

结束时按任务 ID 清理本次创建的分类页和计算器，写回镜像 `1`，将息屏时间恢复到 120 秒，停用 D3 后经有线 ADB 重启。复核三个资格值为 `false`、原模块和 Overlay 状态匹配，并恢复无线 ADB。只读备份确认经典模式布局库仍存在且 SQLite 完整性通过。用户通过系统界面切回经典模式，确认图标位置正常。回退前后的经典库布局记录一致，抽屉模式开关已为 `false`。

用户重接显示器并确认镜像正常。无线 ADB 确认内屏回到原桌面前台，内屏和外屏同在组 0 且物理 `ON/ON`，外屏为 2560×1440 @ 60 Hz。背屏单独在组 1、物理 `OFF/OFF`。

## 原测试条件归档

1. 接回显示器前确认有线回退和同一启动周期的无线 ADB。接入后重新枚举实际外屏 ID，核对同一次连接、组 0、物理 `ON/ON`、独立 layer stack、`canHostTasks=true`、内屏及背屏状态。目标页允许竖屏黑边。
2. 以实际落屏、Activity token、窗口、Surface/VRI、SF 图层和对应 buffer 入队及 latch 串起证据，并由用户确认实体屏幕画面。`HAS_DRAWN` 仅作 WM 线索。区分策略拒绝或改投内屏、采集证据不足、已观察到目标图层无 buffer，以及确认出帧。只有前后台任务可安全恢复时才切走回切一次，按实际 Surface 与图层身份判断是否重建。重建时核对新图层的帧。结束后恢复原前台并复核显示状态。通过仅覆盖分类设置页的 Flutter 对照，次屏 HOME 仍待验证。
3. 若接回后只有镜像，先停在镜像基线。D4 已观察到单写 `0` 会被策略恢复。已有实测的最小候选是复用原 D3 单资源 Overlay（`config_isDesktopModeSupported=true`），在有线 ADB 可恢复的条件下启用并重启一次，接入外屏并核对镜像基线，再保持同一次物理连接临时关闭镜像。这组改动须另行获得明确授权。内屏和背屏会经历重启，外屏切换为独立内容时可能只显示黑底和状态栏。外屏进入背屏组或任一屏异常时停止。执行前记录前台、组、电源、镜像值、输出模式和模块状态。[镜像恢复策略](14-device-mirror-policy-and-mode-routing.md) · [D9 电源对照](17-external-desktop-power-and-composition-control.md)
4. 如获授权实施上述临时改动，收尾时先退出本次测试页并写回原镜像值，使用有线 ADB 停用 D3 后重启。复核测试 Overlay 缺席、三个资格资源和其他模块状态回到采样值，内屏和背屏电源及分组正常，外屏回到原镜像画面与活动模式。需要重新接线时按镜像状态接入，再复核组号。D10 已完成该停用回退。[D10 回退](18-secondary-home-first-frame-control.md)

## 本地证据

原始采集留在 `analysis/local/device-validation/` 下的 `*-D11-stock-flutter-control/`、`*-D11-stock-flutter-control-resume/` 与 `*-D11-stock-flutter-retry/`。ADB platform-tools `35.0.2`，用 `adb -d` 核对有线，外屏接入后使用已核验的无线传输。

- 第一次对照的 `group-transition-logs.txt:434,713–716,748–753,1171,1181,1432` 与 `final-mirror-*` 记录迁组及回退。
- 复测的 `category-first-logcat.txt:2698,2818,3280–3292,3434,3377,3763–3769`，`category-first-windows.txt:125–158`、`category-first-sf.txt:393–394,1092–1102` 和物理截图记录首帧、落屏及内屏模式变化。
- `trace-frame34-thread.json`、`trace-buffer-slices.json`、`trace-frame-timeline.json` 对照切走前旧图层入队、latch 和 present。`category-switch-logcat.txt:3358–3383,3619` 和 `return-guard-logs.txt:140–152` 记录旧 Surface 销毁及随后迁组。
- `layout-recovery-comparison.txt`、`incident-mode-keys-post-restore-*`、`rollback-verified-modules.txt` 和 `final-mirror-*` 记录最终恢复。布局库和截图仅保留本地。
