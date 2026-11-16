# 25 外屏迁组触发条件与休眠恢复

2026-11-16（北京时间），popsicle / `OS4.0.6.0.XPBCNXM` / Android 17。基于 `3c17468249d09b6ef97b38fd6dee1dd353546dac`，复用固定 ROM 与 D9、D11、D12 归档。[ROM 和脱敏实测锚点](../analysis/evidence/external-display-group-recompute.json)

**[ROM] 外屏进入背屏组有两个条件。** 投射资格已经生效，且 Mapper 又执行了分组。分组器计算出 `secondary_mode`，Mapper 却用空的布局名分配组 ID，复用背屏占用的组 1。**[实测归档] D11 和 D12 的空闲迁组均发生在组 0 进入 Dozing 后约 50 毫秒，D9 和 D12 重插时也出现同样的 `reason=1` 迁组。** 两次空闲归档未记录让 Mapper 执行当轮分组的具体设备事件。D11 设为 600 秒时的迁组也没有找到对应的超时、热插拔或首个入队事件。

## 时间线与触发边界

| 对照 | 归档可直接确认的顺序 | 尚缺证据 |
| --- | --- | --- |
| D9，同连接与重插 | 18:16:12.906 背屏 Dream 已要求 OFF。18:16:43.174 关闭镜像，外屏暂留组 0。18:17:10.261 初次分到组 0（`reason=3`）；10.263 重插待选，外屏 disabled，紧接一次物理 ON；18:17:10.275 外屏迁组 1，随后物理 OFF。18:17:19.514 启用，随后物理 ON，外屏显示黑底和状态栏。写回镜像后用户看到镜像恢复，共组快照仍可见。 | 时间线吻合 Mapper 内建第二轮；归档没有入口标记可直接确认。物理 OFF 同时有待启用和组 1 策略两个条件。 |
| D11，120 秒 | 16:36:42.990 关闭镜像，最初外屏仍在组 0。16:36:56.046 PMS 记空闲超时；56.048 组 0 Dozing；56.098 外屏迁组；56.108 LocalDisplayAdapter 设外屏 OFF；56.112 SF 设 Off。16:36:58.432 组 0 已回 Awake，外屏仍 OFF；16:37:37.749 写回镜像后，快照仍共组且 OFF。 | 空闲状态变化之后的首个 Mapper 入口。现场另一次息屏缺独立时间锚。 |
| D11，600 秒 | 16:50:42.118–42.136 分类页退到后台，旧 Surface 销毁。16:51:23.707 内屏有亮度日志；23.708 外屏迁组；23.715 外屏 OFF；23.753 SF 将物理 layer stack 设为 −1。收尾快照的系统设定仍为 600000 ms，组 0 Awake，组 1 Dozing，持有 `0x40`。 | 迁组前 1 ms 的亮度日志只能确认时间相邻。归档没有对应设备 diff、提交状态、布局回调或其他可识别的触发事件。组 0 的 Awake 是事后采样，600 秒是设置值。两者不足以还原当时全部 PMS 输入。 |
| D12，120 秒 | 17:00:53.530 空闲超时；53.533 组 0 Dozing；53.588 外屏迁组；53.603 外屏 OFF。17:01:10.104 记录生物识别唤醒；同连接解锁后组 0 Awake、内屏 ON，外屏仍 enabled、可承载任务、组 1、物理 OFF，DPC 为 DOZE/OFF。 | 与 D11 首轮同样缺首个 Mapper 入口。D12 采集的 tag 列表未包含 DisplayDeviceRepository。 |
| D12，重插 | 17:02:05.383 接入时先分到组 0（`reason=3`）；05.386 disabled、随后物理 ON；05.398 迁组 1（`reason=1`）；05.401 物理 OFF。17:02:26.059 用户选「桌面」，外屏 enabled 且再次物理 ON，仍属组 1。 | 时间线吻合 Mapper 内建第二轮；归档没有入口标记可直接确认。启用后的外屏 DPC 快照仍为 DOZE/OFF。现场有状态栏，HOME 无可绘制内容。 |

时间均为设备记录的北京时间。D9 日志采用 Unix 秒。相关快照和行号见锚点文件与原报告。[D9](17-external-desktop-power-and-composition-control.md) · [D11](23-stock-flutter-external-display-preflight.md) · [D12](24-external-activity-lifecycle-and-idle-power.md)

## [ROM] 哪些入口会重算分组

1. **镜像设置更新资格。** `DisplayManagerService.updateMirrorBuiltInDisplaySettingLocked()` 更新最终镜像值，在内容模式管理开启时遍历逻辑屏，调用 `setCanHostTasksLocked(!mMirrorBuiltInDisplay)`。该入口可发逻辑显示变更通知，本身没有调用 Mapper 的分组遍历。锁任务模式可令最终镜像值为 true，需以 DMS 的有效值核对 secure 设置。D9、D11、D12 的同连接切换窗口正体现了资格和组成员在不同事件中更新。
2. **物理状态变化可触发全表重算。** DPC 选出的物理状态经 DMS 到 `LocalDisplayDevice.requestDisplayStateLocked()`。requested state 比较有变时先改 `mState`，清除设备信息缓存并发 `CHANGED`。执行硬件状态切换后，`setCommittedState()` 改 `mCommittedState`，也发同类事件。`DisplayAdapter` 把设备通知投递到 Handler，Repository 计算 diff 后通知 Mapper。Mapper 的 `onDisplayDeviceChangedLocked()` 完成可推进的设备状态过渡，再遍历全部逻辑屏执行 `assignDisplayGroupLocked()`。内屏、背屏、外屏中的任一设备更新都可使已获得资格的外屏迁组。Repository 对纯 committed-state diff 的日志受 DEBUG 控制，仍通知监听器。亮度分支本身没有直接发这个事件；同次 Runnable 仍可能处理状态变化，厂商回调及其他并发事件也须对齐。SF 的重复 VSYNC 或邻近的应用日志没有提供 Mapper 入参。
3. **热插拔、布局和启用也会走分组。** 本地热插拔回调进 `tryConnectDisplayLocked()` 或 `tryDisconnectDisplayLocked()`，设备新增/移除触发 Mapper 更新。设备状态布局提交、外屏由 disabled 变 enabled 的入口也可触发。新接入的第一轮可先计算 fallback。Mapper 对首次看到的逻辑屏标记 CONNECTED，同时设置 `reloop=true`。同一轮同步派发 CONNECTED，DMS 预处理执行 `setupLogicalDisplay()`，补写有效镜像对应的任务资格，再由外屏策略设为待确认。这里使用底层 `setEnabledLocked(false)`。后处理可下发初始物理 ON。Mapper 发完本轮事件后直接再跑一次，读到已经补写的资格。此路径足以解释 D9/D12 同一线程的 `组 0 → disabled → ON → 组 1`，无须等到 Handler 回收 ON 的设备通知。requested/committed 仍可再触发后续独立更新。用户确认启用则走 `setDisplayEnabledLocked()`，它会显式调 Mapper 更新。初次连接和重新启用都有 DMS 下发 ON 的入口，需要同时观察 DPC 最终请求、DMS requested/committed 和 SF 电源，尤其要检查待选时短暂 ON 是否曝光内容。
4. **分配键丢失派生组名。** D3 缓存的整机资格为 true，内屏资格为 false。布局组名空、`separate_timeouts=true`、EXTERNAL 可承载任务时，Allocator 得到 `REASON_PROJECTED=1` 和 `secondary_mode`。Mapper 用派生名扫描现存组，并因派生非空而要求独立组；但 `assignDisplayGroupIdLocked()` 的名字参数来自 `getLayoutGroupNameLocked()`，值仍为空。此分支不能直接采用搜索结果，随后访问 `mDisplayGroupIdsByName[""]`。背屏有 `FLAG_OWN_DISPLAY_GROUP`，启动时已经以空键占用组 1。组 1 对象也已存在，因而只更新成员，保留原组名和 flags；新建非默认组时按类型和内容模式设置 `FLAG_DEFAULT_GROUP_ADJACENT` 的路径没有执行。JADX 普通输出在这里有损坏的控制流，分支以 fallback 指令为准。

[推测] D11 首轮和 D12 的空闲超时先改变电源请求，随后某个显示设备状态或其他显示信息事件令 Mapper 读取已改变的任务资格。PMS 的 Dozing 转换与外屏分组是不同步骤。D11 的 600 秒对照说明诊断不能只监视超时入口，重插证明热插拔链也足以让分类结果生效。空闲和 600 秒对照的入口均未定位；重插静态链已定位到首次枚举自带的第二轮更新，归档未记录轮次。

[AOSP] 固定参考版本也把原布局名传给分配函数；ROM 的直接采用现成组号条件比参考版多查 `!isOwnDisplayGroup`。当派生名没有命中现存组时，两者均可能回到原布局名查表。此处复用背屏依赖本机的空布局名与背屏独立组，代码对照不足以确定缺陷由哪一版本引入。[固定参考源清单](../analysis/evidence/aosp-sources.json) · [原对照](16-external-desktop-power-group.md)

## [ROM] 为何亮了内屏，外屏仍黑

- Mapper 对成员变化的已有组发 CHANGED。DMS 异步转给 PMS，PMS 更新显示到组的映射，沿用该组的 `PowerGroup` 和 wakefulness；新组 ADDED 才创建初始 Awake 的 `PowerGroup`。组 1 支持双屏机的 Sandman 路径。DreamManagerService 以 token 映射到组，按组写 doze override 并管理组的 doze wake lock。PMS 再用该组的 `0x40` 与 OFF override 产生 DOZE/OFF。D9 有迁组前的 Dream OFF 记录及同一把组 1 锁的前后快照。
- DMS 的 `requestPowerState(groupId,...)` 向该组的 DPC 扇出请求。外屏接收 DOZE/OFF 后可经 DPC、LocalDisplayAdapter 到 SF 的物理 Off（待确认 disabled 也可使它 OFF）。DMS 配置已 OFF 的物理屏时可令 layer stack 为 −1。D12 解锁快照里的 stack 2 是**逻辑**显示的值。它与实际 OFF 可以同时存在。
- 内屏唤醒可由显示定向入口只唤醒目标组；PMS 普通 `wakeUp()` 在 separate timeouts 下遍历组 0 和带邻接 flag 的组。归档中的组 1 flags 为 0。D11/D12 的唤醒结果吻合这两个边界，生物识别日志本身未提供 Binder 入口或目标组枚举。后续若又有设备变化，只要外屏仍是 projected，Mapper 重算也将得到相同的组 1。PMS 对外屏 ID 定向唤醒会命中其当前组，因而会影响背屏。
- **[ROM] 生物识别唤醒补查。** `MiuiSystemUI.apk` 的 `BiometricUnlockController.startWakeAndUnlock()` 可运行带 `android.policy:BIOMETRIC` 的回调。该回调调用三参数 `PowerManager.wakeUp()`。固定 ROM 的 `framework.jar` 将该重载送到普通 Binder `wakeUp()`，带 Display ID 的四参数重载才送到 `wakeUpWithDisplayId()`。D11/D12 的 reason 和 details 与前一路径相符，归档缺少对应 Binder 事务。若投射新组得到 adjacent flag，该生物识别路径按静态条件会把它纳入唤醒枚举，锁屏时序、厂商唤醒过滤及物理恢复仍需验收。
- 原镜像切换回调不及时重算组；D11 写回镜像仍 OFF，D9 写回镜像恢复画面时仍有共组记录。未来验收须同时检查组、电源、合成，以及设置是否稳定收敛。

## [推测] 最小候选与状态机边界

D3 v0.1 是单资源资格对照，安装包内的 APK 只覆盖 `config_isDesktopModeSupported`。D12 回退归档记录该模块保留且停用，原有模块的标记与基线一致。后续离线查证可直接使用 ROM 和归档。候选修正涉及 `services.jar` 的分组与事件路径，现阶段沿用原 D3 包作对照。[D3 资格验证](15-device-desktop-qualification-preflight.md) · [D12 回退](24-external-activity-lifecycle-and-idle-power.md)

**优先验证派生投射组的分配与及时重算。** 只在 Mapper 已经判定 EXTERNAL 为 projected、布局原名为空且 separate timeouts 生效的分支，令分配表使用稳定且独立于空布局键的 `secondary_mode`。复用现有组 ID 分配器与新组 flags 路径。组 ID 由系统分配，不能硬编码为 1 或 2。静态核查名字空间内显式布局是否也可用 `secondary_mode`；若会冲突，则派生键需有独立命名空间，且查找和分配皆使用该键。内置背屏、显式布局、虚拟设备关联和其他分组须各自保持其既有入口。若组已存在，按现有成功路径复用，并验证成员为空时的 REMOVED、重插时的 ADDED 以及 PMS 监听顺序。

分配键单改能消掉碰撞，但不能消掉等待无关设备事件的时间窗。第二处最小改动是让 DMS 在**一批**有效任务资格变化后，在 Mapper 同一锁域排一次合并后的组更新；CONNECTED 复用已有的内建第二轮，在资格和待启用策略都就绪后收敛。优先沿现有更新和分组通知入口核对锁顺序、回调重入与事件先后，避免在逐屏设置回调或 CONNECTED 回调中递归调用整表更新。资格与目标组一致时须幂等。组 0、组 1 的成员变化与新投射组的 ADDED、REMOVED 到达 PMS 时，应按最新成员映射下发，新旧组切换期间仍需满足锁屏和连接确认条件。热插拔需在执行时复核当前逻辑屏和物理连接，丢弃来自旧连接的工作。镜像返回原路径时，须观察组 0 明确接管策略并覆盖旧 DPC 请求。

| 状态与变更 | 候选的预期与风险 |
| --- | --- |
| 镜像与同连接投射反复切换 | 普通镜像外屏进组 0。投射资格稳定后迁入自己的邻接组，回镜像收敛回组 0；组 1 只包含背屏。复核组回调与 WM 任务承载资格一致，并检查旧组的排队请求会否在新请求后短时关闭外屏。 |
| 重插待选 → 「镜像」或「桌面」 | 等待用户确认期间服从 disable、允许条件与锁屏策略。分组本身可以提前计算，若新组 ADDED 初始化 Awake，必须证明禁用屏没有把内容送到 HWC，也不会改变待选或锁屏的电源策略。启用后由目标组稳定接管；一次 DMS ON 不算通过。 |
| 空闲 → 唤醒／解锁 | 新投射组独立计算用户活动；PMS 创建时缓存 adjacent flag，对普通 `wakeUp()` 可纳入，对 `wakeUpWithDisplayId()` 仍只取定向组。非 0/1 组没有 Sandman，空闲路径可直接转 Sleep。相邻组是否 interactive 也参与组 0 的 Doze 判定和全局交互态。须逐条验证电源键、生物识别、定向唤醒及内屏 AOD。 |
| 手动锁定、快速切换、拔线跨过锁屏 | 新组的创建、销毁和重建会改变全局 wakefulness 聚合、Notifier 及可选的 `lockOnPowerGroupDisconnect` 行为。验收须覆盖两次连贯切换、待选时取消，以及未解锁时外屏的锁屏或熄屏策略。 |
| 背屏 AOD 开关和背屏独立唤醒 | 观察组 1 的 wakefulness、Dream token 所属组、doze override 与物理状态。前屏或外屏操作不得唤醒组 1；背屏 AOD 的请求不得扇出给外屏。 |

[待真机] 如果所有正常唤醒入口能使邻接组恢复，分组与重算即可作为最小修正。若生物识别等定向入口仍漏掉新组，先确认具体入口、Keyguard 授权时点及产品所需唤醒行为，再评估仅针对已启用的投射邻接组补齐通知。把投射外屏固定在组 0 可作为对照，其独立超时语义会改变；把背屏 flags 改成 adjacent、强制外屏电源 ON、跳过禁用或直接写 SF/HWC 都会跨越已有电源边界。

## [待真机] 验收和缺证补采

1. **分清触发者。** 在同一单调时间线上记录 DMS 有效镜像值和 old/new `canHostTasks`、LocalDisplayAdapter 入队事件及 requested/committed、Repository 分发设备及 diff、Mapper 更新入口与分配键、组事件、PMS wake/sleep 调用及目标组、Dream token 对应组及 override。每个事件用相关序号串接，记录 DPC 请求与 SF 电源提交。以下一轮 120 秒空闲、600 秒等待、手动锁屏和重插分别复查，避免用时间邻近代替调用链。
2. **电源及隐私。** 按上表分别执行同连接镜像往返、两种重插选择、空闲和手动锁屏、按键／生物识别解锁、锁屏期间重插及背屏 AOD 开关。组 1 始终只服务背屏，锁屏和待选期间无应用画面泄漏；按既有策略应恢复时，外屏无需拔线或重新选模式即可恢复 DPC、DMS 与 SF 的 ON 及正确 layer stack。用已知可落屏的计算器核对实体画面及新图层 buffer；回镜像复核 1440p60 和内屏。
3. **验证范围。** 当前候选、修正后的息屏唤醒、独立模式手动锁屏、次屏 HOME 首帧和点击、原厂 Flutter 回切、输入及高刷均为 `NOT_RUN`。D12 普通 Activity 回切的 PASS 仅覆盖同 ActivityRecord、不同 VRI 及新图层出帧。

## 次屏 HOME 与原厂 Flutter

D10 的组 0/物理 ON 对照已有计算器可见，HOME 初建和重建仍无可绘制内容。D11 证明原厂 Flutter 的指定 scene/entrypoint 能在相同拓扑产出内容，不能证明 HOME 已绑定自己的内容。HOME 先要证明可达的内容入口及属于该 scene 的窗口，之后再验证首帧通知绑定当前 Surface：创建时捕获该次 Surface 身份，销毁时使其失效，迟到回调与当前 Surface 不同则丢弃。D10 的同 token、不同 VRI 是测试这一边界的依据。D11 原厂分类页只证明旧 Surface 在切走时销毁，回切仍为 `NOT_RUN`。[D10 对照](18-secondary-home-first-frame-control.md) · [scene 生命周期](21-secondary-home-scene-lifecycle.md) · [首帧绑定](22-secondary-home-first-frame-entry.md)

**[实测归档] 分类页启动触发了共享模型切换。** D11 分类 scene 的 Dart 线程在 16:48:25.323 进入 `categorySettingsPage → _startApp`，25.342 准备模式切换动效，25.343 依次记录 `_loadCurrentLauncherMode` 得到 drawer、`_applyModeChangeCore` 选 drawer、`LauncherModelManager.onLauncherModeChange` 加载 drawer。随即 FRB worker 记录 `change_launcher_mode`、共享控制器的 `desktop → drawer`、待处理任务失效和布局库切换。初帧出现在这之后。归档中还有下一次 getter 返回 false 的记录，不能用单条 getter 日志推断已回退，实际现场和布局库体现了共享模型切换。

**[ROM] Dart 到 Rust 的共享写入点。** `_refreshLaunchMode 0x192da38` 有两条调用 `prepareInAnimation` 后进入 `_applyModeChangeCore 0x8e15a4` 的路径。与实测顺序一致的共用链从 `0x8e15bc` 读当前模式，`0x8e19a0` 调 `onLauncherModeChange`，`0x192e568` 调 `LauncherModel.changeLauncherMode`，`0xa7a400` 进入生成的 RustLib API，`0xa7a4e4` 提交 FRB 普通任务。Rust 生成的主分发器在 `0x7fae60` 跳到同名 wire 方法；对应 worker 体从全局地址 `0xf2a348` 读控制器指针，在 `0x560dc0` 调 `LauncherModeController::change_launcher_mode`。控制器在 `0x72cb00` 写共享对象的字段，随后通过 `LauncherDataManager::instance` 取共享模型，在 `0x72cc68` 调 `switch_db`。这解释了新增外屏 scene 能影响内屏工作区的路径。分类入口到首次模式刷新的精确异步回调，以及持久化开关由谁先写，当前证据仍不足；共享控制器写入与切库已有静态和运行时锚点。[D11 日志和 AOT 地址](../analysis/evidence/external-display-group-recompute.json)

## 复查方式

用锚点文件列出的本地相对路径、行号和 SHA-256 对照现有提取产物。ROM 主输入是 `services.jar`，哈希和 DEX 清单见组件清单。正常 Java 输出复用原先 JADX 1.5.6 结果；Mapper 用原 `desktop-power-fallback`，亮度方法补用相同工具的 fallback。对应复现命令如下，均只写本地反编译目录。[组件清单](../analysis/evidence/components.json) · [已有复现说明](../analysis/README.md)

```powershell
$jadxJar = 'tools/bin/jadx/lib/jadx-1.5.6-all.jar'
$servicesJar = 'extracted/files/system/system/framework/services.jar'
java -Xmx5g -cp $jadxJar scripts/SelectiveJadx.java $servicesJar analysis/local/jadx/group-recompute-fallback 'com\.android\.server\.display\.LocalDisplayAdapter$' fallback
```

Launcher 地址使用 ARM64 ELF 虚拟地址。用既有本地 `analysis/local/aot-secondary/aot_dis.py`、`aot_refs.py` 和 `native_dis.py`（NDK LLVM 30.0.15729638）分别复查 Dart 直接分支、反向调用和 Rust 路径。示例为 `python analysis/local/aot-secondary/aot_dis.py 0x8e15a4` 和 `python analysis/local/aot-secondary/native_dis.py rust 0x72c52c 0x72d1a8`。
