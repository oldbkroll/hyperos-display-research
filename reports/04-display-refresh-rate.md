# 04 外接刷新率与显示链路

本轮没有连接手机，也没有 EDID、显示器 OSD、HWC 实际 mode 或链路训练记录。**已定位一个条件性的 60 fps 渲染投票；尚未证明外接物理输出的 60 Hz 唯一根因。**

## 一、已追踪的 Framework 策略

**[ROM]** `odm/etc/build.prop:147`：`vendor.display.support_builtin_high_fps_when_pluggable_connected=0`。单看名字只涉及连接外屏时的内建屏高帧率，不能直接称为外屏物理刷新率限制；继续追踪方法后，能确定它也参与全局渲染投票。

**[ROM] F12–F15**（哈希、方法行号见 [findings.json](../analysis/evidence/findings.json)）：

1. `DisplayModeDirectorImpl` 构造时读取属性，保存到 `mBspSupportExtraDisplayHigRefreshRate`，仅值为 1 才为 true。
2. **F22** `DisplayAdapter` 派发设备事件到 `DisplayAdapterImpl.updateExternalDisplayStatus()`，对 EXTERNAL 的添加/移除写入 System `external_display_connected`。**F23/F12** 原生 DisplayModeDirector 经已注册的厂商 provider 调用 `registerMiuiContentObserver()`，监听该键、注册 display listener 并刷新实际显示状态。
3. `queryExternalDisplayEnabled()` 枚举 display，要求 type=EXTERNAL 且 DMS `isDisplayReadyForMirroring()` 返回 true。
4. 本 ROM 的 `ExternalDisplayPolicy.isDisplayReadyForMirroring()` 只检查 boot completed、逻辑显示存在、外屏类型和 enabled。**方法体没有检查当前 content mode 是否为镜像**，所以不能推断独立桌面必然避开此策略。
5. 属性不为 1 且外屏实际启用时，`shouldExtraDisplayLimitRefresh()` 返回 true。`getMiuiRefreshRateRange()` 返回范围 0–60；另一个 `mMultiDisplaysLimit` 条件也可触发相同范围。
6. MIUI optimization 路径启用时，`updateMiuiRefreshRateSettingLocked()` 使用 `Vote.forRenderFrameRates()`，以 priority 24 写入 global vote。`VotesStorage.getVotes(displayId)` 将全局投票合并进各显示，除非该显示同优先级已有局部投票。

**[ROM]** `RefreshRateVote.RenderVote.updateSummary()` 缩紧 render 范围上限，同时更新 physical 下限；它没有像 PhysicalVote 一样直接缩紧 physical 上限。因此它能限制渲染策略，**不能等价表述为 HWC 必定输出 60 Hz**。最终模式还受其他投票、帧率覆盖、模式切换策略和已暴露 supportedModes 影响。

**[ROM] F24** 下游 `VoteSummary.validateModeWithinRenderRefreshRange()` 在不支持 frame-rate override 时，直接按 render 范围排除物理 mode；支持覆盖的普通分支则还检查 vsync/maxRender 是否接近整数比。因此上述 60 投票**可能进一步筛掉高刷 mode**，也可能保留可按整数比渲染的高刷 mode，不能把渲染与物理完全割裂。实际 mSupportsFrameRateOverride、候选模式和筛选日志仍未测量；这不改变“尚未证明物理 60 Hz 唯一根因”的结论。

属性若为 1，会走另一个分支：将 `miui_refresh_rate` 向下取整为 60 的倍数，并至少使用 60；热限制等条件仍在。故改属性不等于解除所有限制，更不等于新增 120/180 Hz 物理模式。`mMiuiRefreshRateEnable`、连接设置、实际 enabled 状态及投票是否存在，必须通过未来 dumpsys 验证。本轮不关闭 MIUI optimization，也不修改任何属性。

## 二、Vendor / HWC 已确认与未确认

**[ROM]** VINTF 声明 `android.hardware.graphics.composer3` AIDL v4 / IComposer/default，厂商服务为 `/vendor/bin/hw/vendor.qti.hardware.display.composer-service`；另有 QTI display.config v13 及 Xiaomi mihwcextension v2。init 配置定义其重启会重启 SurfaceFlinger，因此不把直接重启 HWC 作为低风险操作。

**[ROM]** 显示相关二进制及哈希见 [vendor-binaries.json](../analysis/evidence/vendor-binaries.json)。`libsdmcore.so`、`libsdmclient.so`、`libsdedrm.so` 保留可定位的 pluggable/DRM 显示符号；已使用本机 NDK LLVM 21.0.0 只读反汇编以下路径：

| 文件 / 方法 | ELF 虚拟地址 | 本轮所见与边界 |
|---|---|---|
| libsdmcore / DisplayPluggable::GetRefreshRateRange | 0x16e938 | 从对象字段取范围，或调用 DisplayBase；实际范围值未知 |
| libsdmcore / DisplayPluggable::SetRefreshRate | 0x16ea30 | 存在状态检查、间接硬件调用和 ReconfigureDisplay；不是模式支持证明 |
| libsdmcore / DisplayPluggable::GetOverrideConfig | 0x172754 | 调用 Debug::GetExternalResolution，再调用硬件对象查询配置 |
| libsdmutils / Debug::GetExternalResolution | 0x18640 → 0xc840 | 读取字符串标识 `vendor.display.hdmi_cfg_idx`，检查结果非空；值格式与后续硬件解析未完整恢复 |

这比只搜索属性名更具体，但仍不足以给出可用 override 值。`hdmi_cfg_idx` 可能与配置索引有关，不能把分辨率字符串、任意索引或另一设备参数直接套入。

`vendor.display.pluggable_vsync_prioritized=true` 也同时出现在 ODM 属性和 SurfaceFlinger 二进制标识中；消费路径尚未完整恢复，列为线索，**不据此证明任何刷新率**。

## 三、不能混淆的量

| 观察量 | 可以说明什么 | 不能说明什么 |
|---|---|---|
| 游戏/应用 FPS | 应用提交或渲染节奏 | DP 物理时序 |
| renderFrameRate / desired render range | Android/SF 的渲染策略 | HWC 已选择同数值 mode |
| 外屏 Display supportedModes | Framework 收到的模式集合 | 未上报模式实际可用或信号稳定 |
| SF 活动物理 mode / HWC config | 合成/输出端选择 | 接收端实际工作稳定及线缆长期可靠 |
| 显示器 OSD + EDID/DRM | 接收能力、输入时序交叉证据 | 全部应用的渲染 FPS |

`ro.vendor.display.default_fps=60`、`supported_automode_maxfps_list=60,120`、游戏默认 60、背屏 orientation、虚拟屏 120 等不能单独证明外接 DP 上限。两块内建屏的 displayconfig 文件也不能作为外接 EDID 模式表使用。

## 四、分辨率与黑边

镜像通常需要把手机画面按比例放入外屏，可能有黑边；独立外屏任务使用外屏逻辑尺寸，是另一问题。逻辑 `wm size/density` 修改可能影响 UI 布局，不能替代更改 HWC 输出时序。需分别记录接收端输入分辨率、SF 活动 mode、外屏逻辑尺寸和镜像 viewport，才能区分链路降档、等比镜像和应用 letterbox。

本轮发现了 external action-safe width/height、external downscale 等二进制标识，尚未完整追踪默认值/作用条件，不建议直接修改来处理黑边。

## 五、未来如何判断 60 Hz 出在哪层

1. 外屏 supportedModes 只有 60：优先对比 EDID、HWC/DRM modes、转接器及链路，不能先归因于 Launcher。
2. supportedModes 有高刷，但 priority 24 render vote 为 60：先确认上述调用链运行条件，再隔离测试策略；同时看 physical 和 render 是否分离。
3. Framework/SF 请求高刷，HWC 仍选择 60：检查 composer 日志、带宽/并发限制和请求失败原因。
4. HWC/SF 报高刷但 OSD 为 60：继续检查显示 ID、虚拟/物理混淆、转接器转换和接收端。
5. 各层都显示高刷：仍需持续负载、热状态、内屏正常工作及输入验证，才能通过功能验收。

完整只读采集和风险分级见 [06](06-device-validation-plan.md)。内核、DTBO 和 USB-C/DP 训练日志尚未分析；没有制作底层补丁。
