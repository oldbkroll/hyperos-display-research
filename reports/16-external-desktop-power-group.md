# 16 原生外接桌面黑屏与背屏电源组

2026-11-11（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`。复查[报告 15](15-device-desktop-qualification-preflight.md)的 D3 快照和匹配 ROM。完成离线追踪后，用户接通无线 ADB 并授权采集 D8 原厂基线。同一次启动的 D9 桌面对照及停用回退见[报告 17](17-external-desktop-power-and-composition-control.md)。

## 已保存的真机对照

| 快照 | 组 0 | 组 1 | 外屏 DPC 与物理输出 |
| --- | --- | --- | --- |
| D7 原厂镜像，`00-dms.txt:513–553`、`00-power.txt:402–428` | 内屏 0、外屏 2，`Awake` | 背屏 1，`Dozing`，wake-lock summary 为 `0x40`，有 `dream:doze:1` | `BRIGHT/UNKNOWN`，物理 `ON/ON` |
| D3 单资源 Overlay，原生桌面，`desktop-dms.txt:513–553,2173–2220` | 内屏 0，DPC 为 `BRIGHT/UNKNOWN` | 背屏 1、外屏 2，组名为空、flags 为 0。两块屏的 DPC 都是 `DOZE/OFF`，reason 为 `UNKNOWN` | 外屏逻辑 enabled、可承载任务、有内容、layer stack 为 2；物理 `OFF/OFF`、layer stack 为 `-1`。HOME 与计算器的外屏物理截图均全黑 |
| D3 同一次启动写回镜像，`d1-restored-dms.txt:10,513–553,2174–2220` | 内屏 0 | 背屏 1、外屏 2，仍共组 | `mMirrorBuiltInDisplaySetting=true`、外屏基础 DisplayInfo 的 `canHostTasks=false`，该快照仍为 `DOZE/OFF` 和物理 `OFF/OFF` |
| D8 回退后原厂镜像，`display.txt:513–553`、`power.txt:394–420` | 内屏 0、外屏 2，`Awake` | 背屏 1，`Dozing`，wake-lock summary 为 `0x40`，持有 `dream:doze:1` | `BRIGHT/UNKNOWN`，物理 `ON/ON`，SF 合成已启用 |

D3 的两次 DMS 快照都显示 `separate_timeouts=true`。外屏设备类型为 EXTERNAL，物理设备标记里没有 `FLAG_OWN_DISPLAY_GROUP`。背屏设备有该标记。D3 的实际镜像恢复由卸载 Overlay、重启、重新接外屏后的现场画面确认。写回设置时的快照只证明该时点仍共组，单独改设置后是否会在后续事件中重分组仍待测。

D3 没有桌面激活时段的 `dumpsys power`、`dumpsys dreams` 或连接前后的 PMS/Dream 时间线。D7 可以确认背屏组在原厂镜像下已正常持有 doze wake lock 并发送 `DOZE/OFF`。D3 外屏实际收到了同形请求，但组 1 在那次插线前是否已处于 Dozing、是否曾被唤醒、谁最后一次写入 OFF，均缺少对应的运行时记录。

D8 经无线 ADB 核对当前 ROM、`framework-res.apk` 哈希和镜像值 `1`。三项资格均为 `false`，Android Overlay 列表与 D3 回退后一致，测试 Overlay 已卸载，原有 8 个 KernelSU 模块的标记与保存的基线相符。无线 ADB 的 root 可用，有线回退路径仍需在下次有状态实验前确认。D8 复现了 D7 的组成员和电源策略。成对采集的 DMS 显示外屏 1440p120，SF 的外屏活动模式及 HWC 则同时为 2560×1440 @ 60 Hz。D8 只记录该差异，无刷新率写入或现场 OSD 记录。

[ROM] `DreamManagerService.dumpInternal()` 打印 `mCurrentDream`，未列出双屏分支使用的 `mCurrentDreams`。D8 读到 `mCurrentDream=null` 时，PMS 仍记录组 1 的 `dream:doze:1`。下次判断组 1 的 Doze 来源应结合 PMS 和 Dream 的事件时间线。

## [ROM] 从桌面资格到复用背屏组

1. `LogicalDisplayMapper.onBootCompleted()` 初始化 `DisplayGroupAllocator`，后者缓存整机桌面资格和内屏桌面资格。镜像设置变化时，`DisplayManagerService.updateMirrorBuiltInDisplaySettingLocked()` 在内容模式管理开启时更新任务承载资格，由 `LogicalDisplay.validateCanHostTasksLocked()` 保留各屏校验。该设置回调没有直接要求 Mapper 重新分组，设备增删和信息变化会进入 Mapper 的更新路径。
2. 本轮 D3 的输入条件为整机可进桌面、内屏不支持桌面、EXTERNAL 可承载任务。布局组名为空且 `separate_timeouts=true` 时，`DisplayGroupAllocator.getContentModeForDisplayLocked()` 选 `REASON_PROJECTED`，`decideRequiredGroupTypeLocked()` 返回 `secondary_mode`。因此 Mapper 判定外屏需要自己的组。
3. `LogicalDisplayMapper.assignDisplayGroupLocked()` 用派生类型查找现有组，分配组号时仍传 `display.getLayoutGroupNameLocked()`。`assignDisplayGroupIdLocked()` 的直接采用已查得组号分支要求 `!needsDeviceDisplayGroup && !isOwnDisplayGroup`。需要独立组时按传入的布局组名查 `mDisplayGroupIdsByName`。背屏凭 `FLAG_OWN_DISPLAY_GROUP` 已用空布局名取得组 1，外屏也以空名查到同一个 ID。Mapper 复用已有组，新建组时设置名称和 `FLAG_DEFAULT_GROUP_ADJACENT` 的分支不会执行。D3 实际看到的空组名、flags 为 0、两块屏同组，与该分支吻合。

[AOSP] 固定参考版本的 `LogicalDisplayMapper` 也把原始布局组名传入分配函数。该版本的直接采用组号条件仅检查 `!needsDeviceDisplayGroup`，本 ROM 还检查 `!isOwnDisplayGroup`。当查不到 `secondary_mode` 时，两者都可能继续用原始布局名查表。背屏先占用空名组是这里的设备条件，参考版本的源码不能确定差异的引入时间。[固定版本的源码清单](../analysis/evidence/aosp-sources.json) · [AOSP LogicalDisplayMapper](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/display/LogicalDisplayMapper.java#1204)

## [ROM] DOZE/OFF 的生成与下发

- **组成员变化。** Mapper 对仍有成员的已有组发送 CHANGED，经 DMS `deliverDisplayGroupEvent()` 到 PMS `DisplayGroupPowerChangeListener.onDisplayGroupChanged()`。监听器更新 Display ID 到组 ID 的映射，复用已有 `PowerGroup`，通知 `onGroupChanged()` 并重新计算电源状态。新建 `PowerGroup` 并初始化为 Awake 的路径在 ADDED 事件上。已有背屏组增加外屏成员本身不触发该初始化，也不调用 `wakePowerGroupLocked()`。
- **`policy=DOZE`。** `PowerManagerService.updatePowerStateLocked()` → `updatePowerGroupsLocked()` → `PowerGroup.updateLocked()` → `updateScreenPolicyLocked()`。组处于 Dozing、持有 `0x40` doze wake lock、且不在 powering-on 时，可选中 `POLICY_DOZE`。双屏机的组 1 还被 PMS 视为支持 Sandman 的背屏电源组，具备 Dozing 路径。D7 的组 1 字段符合这个分支。
- **`dozeScreenState=OFF`。** `DreamManagerService.startDozingInternal()` 在双屏机上走 `handleDozingForMultiDisplay()`，从 dream token 解析组 ID，将屏幕状态交给 PMS 的 `setDozeOverrideFromDreamManager()` 并管理组 doze wake lock。PMS 按组存 `RearDeviceDozeScreenState`，`updatePowerGroupsLocked()` 按组读取。策略是 DOZE 时，`PowerGroup.updateLocked()` 把该屏幕状态写进请求。其初始值为 UNKNOWN。D3 请求里的 OFF 是上游给出的具体状态值，`UNKNOWN` 是该请求的 reason。D3 当次写入 OFF 的 dream、时间和调用记录仍缺。
- **物理层清空。** DMS `LocalService.requestPowerState(groupId, request, …)` 遍历组内成员，向可 blank 的显示控制器发送同一请求。D3 外屏的 `mDozeStateOverride=0`，`DisplayStateController.updateDisplayState()` 会按请求的 `dozeScreenState=OFF` 选 OFF，保留本来的禁用、过渡、距离传感器校验。物理 OFF 后，DMS `configureDisplayLocked()` 以 blank 配置 `LogicalDisplay`，物理 layer stack 设为 `-1`。D3 快照中外屏逻辑 enabled 且未过渡，距离传感器没有要求灭屏。DMS dump 里另一个 `mIsDisplayEnabled=false` 来自 `AutoBrightnessFallbackStrategy`，原厂外屏物理 ON 时也为 false。

[推测] 外屏加入已有背屏组时继承了该组正在使用的 Dozing 和 OFF override。即使当次曾经短暂唤醒后重新进入 Dozing，快照中的黑屏也可以由同一组请求解释。首次连接到黑屏期间的事件顺序需要补采。

## 唤醒入口与最小真机对照

[ROM] 窗口与 Activity 有显式点亮分支，分别经 `WindowState` 或 `ActivityTaskSupervisor` 向 `PowerManager.wakeUp(…, displayId)` 发请求。任务已 resumed 本身不能证明进入这些分支。ROM 还有 `cmd power power-on <displayId>`，经 Binder `wakeUpWithDisplayId()` 检查 `DEVICE_POWER` 后，将 Display ID 映射为组 ID，再经 `wakeupDisplayGroupsLocked()` → `wakePowerGroupLocked()` → `PowerGroup.wakeUpLocked()`，保留系统就绪、强制休眠、背屏省电等检查。D3 拓扑下对外屏 ID 使用该命令会请求唤醒**整个组 1**，组内含背屏。将它排除出本轮单屏对照，同样不使用直写 SF/HWC 电源模式或全局电源策略。

以下为 D8 基线后制定的对照计划。D9 执行时采用停用回退，实际步骤和结果见[报告 17](17-external-desktop-power-and-composition-control.md)。

| 步骤 | 单次启动内的操作与判据 |
| --- | --- |
| 原厂基线与回退检查 | 先确认当前 ROM、用户、三项资格值、原有 8 个模块状态、测试 Overlay 缺席、镜像原值和内屏、背屏状态。实际确认有线 ADB、root 和卸载入口。若接显示器时要拔数据线，先验证无线 ADB，并保留可拔外屏后切回有线的路径。条件未满足时停在原厂基线。 |
| 记录启动后的对照 | Overlay 生效后先保持镜像，手机解锁。采一次成对的 `dumpsys power`、`dumpsys display`，记录外屏的动态 Display ID、物理 ID、组及背屏状态。镜像基线宜见组 0、物理 ON 和可见画面。连接前启动带时间戳的 main/system/events logcat 采集。 |
| 只切换外屏内容模式 | 同一启动周期、同一线材和 1440p60 下，使用系统连接弹窗的桌面选项（若可用），或在已批准的范围内按 D3 条件使镜像值为 0 后重接外屏。内屏继续解锁，背屏按原设置运行。保留切换前、首帧或黑屏时、稳定后的 `dumpsys power`、`dumpsys display`、`dumpsys dreams`、外屏 SF/物理截图和现场画面。比对 `Setting new display group`、`Dream requested to start dozing`、`setRearDozeState`、`Waking up power group`、DPC 的 `setPowerMode`。记录 group membership、wakefulness、wake-lock summary、last wake/sleep reason、请求、实际/已提交状态和物理 layer stack。 |
| 判定是否继承背屏策略 | 若组 1 在切换前后均为 Dozing、保有同一个 `dream:doze:1`、两块屏均收到 `DOZE/OFF`，且外屏从 ON/有效 layer stack 进入 OFF/`-1`，可验证成员变化复用了已有策略。若有独立的 wake/sleep 或 dream override 变化，用时间线定位触发者。若外屏已独立成组仍 OFF，按该组策略、DPC 状态和物理提交结果重查。 |
| 可选的正常背屏事件 | 仅在用户同意且无需改设置时，记录一次原生背屏正常点亮和回落。先确认仍是组 1 共组，观察组请求、两块屏物理状态以及外屏是否出现独立内容。若外屏 ON 且绑定 layer stack 2 后仍黑，再进入 SF/HWC 或窗口可见性排查。背屏交互触发后组状态没有变化时，该子对照无结论。 |
| 收尾 | 停止测试任务，恢复原镜像值并核对实际组号和画面。若设置已恢复但仍共组，拔下外屏，按镜像状态重接并复查。若仍异常或采集失联，切回有线 ADB，按报告 15 卸载该测试模块并重启。卸载后核对三项资格、原有模块、内屏与背屏，以及 1440p60 镜像。报告 15 验证过一次 RescueBrick 回退和有线 ADB，KernelSU 内置安全模式仍未验证。 |

计划将所有对照放在一次 Overlay 启动周期。按已验证载体，安装生效和卸载回归各需一次重启。插拔与内容切换无需为每个采样点重启。任何内屏或背屏异常都结束对照，进入恢复。原始输出放在本地。

[推测] 若确认共组继承，下一步优先评审 Mapper 中对物理 EXTERNAL 的派生组名分配，让它在 projected 模式获得独立组，并保留背屏现有 ID、AOD、镜像、拔插及系统电源校验。独立组的初始化、锁屏、唤醒和退出策略仍需验证。当前没有实施分组修改。

## 复查锚点

ROM JAR 以 [组件清单](../analysis/evidence/components.json) 的 `services.jar` 和 [输入副本清单](../analysis/evidence/input-copies.json) 的 `miui-services.jar` 为准，已核对 SHA-256。下列 Java 行号用于定位本地 JADX 1.5.6 输出。Mapper 的普通反编译有重复分支，决定组号的实参、分支条件和 adjacent flag 均已用 fallback 指令复核。[复现参数](../analysis/README.md#外屏电源组)

| 本地分组 | 类和行锚点 |
| --- | --- |
| `jadx/services/sources/com/android/server/display/` | `DisplayGroupAllocator.java:31–85`；`LogicalDisplayMapper.java:538–545,798–814`；`DisplayManagerService.java:1169–1190,2985–2989,3777–3784,3974–3992,6361–6378`；`LogicalDisplay.java:476,673–708`；`state/DisplayStateController.java:24–59` |
| `jadx/desktop-power-fallback/sources/com/android/server/display/` | `LogicalDisplayMapper.java:428–467,491–625` |
| `jadx/services/sources/com/android/server/power/` | `PowerManagerService.java:573–585,608–617,662–700,2082–2125,2151–2173,2328–2351,3716–3766,4719–4729,6117–6135,7211–7234`；`PowerGroup.java:275–291,441–515`；`PowerManagerShellCommand.java:99–105,143–150,666–686` |
| `jadx/services/sources/com/android/server/` | `dreams/DreamManagerService.java:1061–1111`；`wm/ActivityTaskSupervisor.java:2482`；`wm/WindowState.java:2116` |
| `jadx/desktop-power-miui/sources/com/android/server/power/` | `PowerManagerServiceImpl.java:2097–2099,2249–2271,2483–2501` |

设备文件路径以 `analysis/local/device-validation/` 为根。D3 使用 `*-D3-overlay-idmap` 内的 `desktop-dms.txt`、`d1-restored-dms.txt`、`d1-mirror-restored.txt`、`desktop-sf.txt`、`d1-sf-active.txt` 和物理截图。D7 对照在 `*-D7-mirror-lock-wake`，包含 `00-dms.txt` 与 `00-power.txt`，后者在第 221 行记录 `dream:doze:1`。D8 在 `*-D8-stock-power-preflight`，采样时间与哈希见 `capture.json`。D8 的 `power.txt:213` 记录 `dream:doze:1`，`mode-pair-surfaceflinger.txt:142–145,2691–2702` 记录 1440p60。原始设备日志与 ROM 派生代码留在本地。

本轮通过本仓库两个验证脚本的 `--local` 完整性核验，并对三份 DMS 快照的成员、请求、物理状态和 layer stack 做了字段断言。原有核验记录保留，本轮通用核验输出保存到 `analysis/local/desktop-power-verification.json`。
