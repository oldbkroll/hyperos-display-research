# 19 次屏 HOME 的渲染宿主与首帧同步

2026-11-12（北京时间），popsicle / `OS4.0.6.0.XPBCNXM`，从 `aa563b7` 续查。输入来自同版 ROM 和已归档的 D10。新增设备验证为 `NOT_RUN`。[ROM、指令、重定位与 D10 锚点](../analysis/evidence/native-first-frame.json)

**[ROM] 缺失的调用边位于 Launcher 窗口接到 Surface 之后。** 主屏 Launcher 的活动回调创建 Flutter shell，其窗口回调把 `NativeWindow` 交给 Flutter。当前 ROM 的 `SecondaryDisplayLauncherUi` 返回有效窗口描述符，但同一组活动与窗口回调只记录日志、释放实参或返回默认值。具体到 D10 的窗口，运行库已提供 BLAST Surface，次屏回调释放了传入的引用，未建立主屏那样的 Surface 到 Flutter 宿主的绑定。绘制同步超时有独立的空事务完成路径。

## 真机 D10 的同一窗口与重建

在同一次启动、同一条物理连接内关闭镜像，Display 2 保持组 0、物理 `ON/ON`、layer stack 2。进程 PID 6516 的次屏活动 token 为 `12970367465612758864`，WM 窗口为 `3f30d8e`，task 64。以下各行的数字为原始文件的行号。

| 对照点 | 证据 |
| --- | --- |
| 18:31:28.176，次屏 HOME 创建 | `live-logcat.txt:38225` 的 `SecondaryDisplayLauncherUi::on_create` 带该 token |
| 18:31:28.190–28.193，Surface 创建 | `live-logcat.txt:38473,38511,38518` 绑定 WM 窗口和 VRI 图层 **232**，尺寸 2560×1440，BLAST Consumer 5。第 38543–38546 行记录该 token 的创建、尺寸变化及首次同步计时 |
| 18:31:29.270，绘制同步完成 | `live-logcat.txt:39071,39332–39334` 对应最后一次计时与超时。同 token、`seq:6`、`has_tx:false`、`render_target_valid:true`、`sc_valid:true`、`window_stopped:false` |
| WM 和 SF 对照 | `live-logcat.txt:39342–39357` 记录图层 232 的 `finishDrawingLocked` 和 show。随后 `home-windows.txt:125–157` 为 `HAS_DRAWN`、`shown=true`，`home-sf.txt:619–635,952` 在外屏 stack 2 列出该 VRI 图层，状态为 `invisible reason=nothing to draw` |
| 计算器退出后，同一 HOME 重建 | `live-logcat.txt:44159–44178,44202–44205,44764–44766` 关联同一 WM 窗口、同一活动 token 和新的 VRI 图层 **273**。仍为 2560×1440，仍在超时后以 `seq:6, has_tx:false` 完成。随后 `home-return-sf.txt:648–651` 对 273 也报告无可绘制内容 |

按两个次屏 BLAST 队列的 ID `197400000007`、`197400000009` 搜索全份 D10 日志，仅在 `41914,45729` 找到 consumer 断开，均为 `api:0,p:0,c:6516`。同进程主屏 Launcher VRI **156** 在 `home-sf.txt:578–581,2221` 有 buffer、frame 655 及物理合成记录，在 `live-logcat.txt:79599` 有 `api:1,p:6516` 的 producer 断开记录。该证据支持两个次屏队列在观测时没有接入同样的生产者。日志开始时主屏已运行，现有日志无法完整复演它的第一帧或排除曾瞬时接入的生产者。

复核 `home-physical.png` 的 RGB 像素，1,127 个非黑像素均位于顶部状态栏区域，中央四分之一面积内为 0。计算器图层 **265** 在同一外屏有 buffer、frame 6 并进入 HWC，`calculator-physical.png` 的同一区域有 848,319 个非黑像素。画面居中源于固定方向 Activity 的 letterbox。计算器证明该次连接可以合成普通 Activity 的内容，它的绘制实现与 Rust/Flutter Launcher 独立。HOME 回切截图与计算器截图哈希相同，回切结论取自稍后的 SF 快照。[D10 对照及回退](18-secondary-home-first-frame-control.md)

## [ROM] 次屏回调与主屏的分流

下文 ELF 地址是各库的虚拟地址，槽位偏移以相应表的首地址为基准。运行库的 `FfiUi` / `UiWindow` 符号和取槽指令确定回调名称。

次屏类名比较在 `libapp_launcher.so:0x94e434–0x94e448`，匹配后直接在 `0x94e44c–0x94e464` 返回活动描述符 `0xe1d318` 及固定数据值。该分支无需构造 Launcher 渲染对象。活动 `on_create`（`+0x18 → 0x776854`）取 token、按日志级别打印，再释放 `UiComponentData`。启动、恢复、暂停、停止和销毁的五个槽均落在直接返回的 `0xd49a28`。请求权限结果槽 `+0x90 → 0x775ea4` 走参数清理路径。其余事件槽的目标也列于证据清单。活动 `request_window`（`+0x48 → 0x776834`）直接返回窗口表 `0xe1e1f8` 和固定数据，未分配逐窗口渲染状态。

| 次屏窗口槽 | 目标及效果 |
| --- | --- |
| `+0x18` attached | `0xd49bdc` 释放传入的 `WindowOperation` 和 Binder 引用 |
| `+0x20` surface created | `0x77a110` 调用指标向量析构，然后释放 `WindowDisplayInfo` 和 `NativeWindow`。析构目标 `0x17d504` 的证明见[报告 12](12-native-secondary-home-display-routing.md) |
| `+0x28 / +0x30 / +0x38` changed / destroyed / view metrics | `0xd49c40` 释放显示信息，`0xccbb98` 直接返回，`0xd49c48` 尾调指标向量的清理槽。运行库在 `0x1a7864–0x1a7878` 派发指标变化 |
| `+0x40 / +0x48 / +0x50 / +0x58` vsync / detached / configuration / focus | `0xd49c58`、`0xccbb98`、`0xd49c5c`、`0x73df00`，配置槽释放对象，其余直接返回 |
| `+0x60 / +0x68 / +0x70 / +0x78` key / motion / version / shortcuts | 释放输入事件、返回版本 2、返回固定快捷键结果。没有触发首帧或应用启动的调用 |

运行库先把根 Surface 作为 `NativeWindow` 加入窗口的 surface group（`0x1a6d84–0x1a6d90`），再通过 `0x1a6f10` 派发窗口创建回调。子 `SurfaceView` 的创建/变化派发位于 `0x1a6cf4 / 0x1a7014`，对象来自已有的子视图集合。次屏的活动及窗口创建回调未往该集合注册渲染视图。邻接的 `0x77a14c` 是另一槽的独立函数，其中 `0x77a2d0` 调用首帧通知。次屏 `0x77a110` 在 `0x77a148` 已尾调释放引用，`0xe1e218` 也只重定位到 `0x77a110`。

主屏类名在 `0x94dc08–0x94dc64` 以内联比较识别。`0x94dd68` 的现有对象状态分支在 `0x94dd94` 或 `0x94e4a8–0x94e4c8` 汇合到 `0x94e4cc`，再经 `0x94e4e0 → 0x5c0444` 构造主屏活动，返回 `FfiUi` 表 `0xe1c438`。相比次屏，主屏有以下三条明确调用边。

1. **构建宿主。** 工厂在 `0x5c06dc → 0xd42db8` 装入原生回调表 `0xf06560`，再进入 `0xb9e6a4`。活动 `on_create`（`0xe1c450 → 0x766074`）在 `0x76612c` 调 `0xb9d430`。该函数按是否存在可复用的宿主，走接口 `+0x50` 的 `shell_holder_spawn`（调用点 `0xb9d7e8`，Flutter 端 `0x6e6c38`），或 `+0x40` 的构建路径（调用点 `0xb9d8f0`，Flutter 端 `0x6e6754`）。这两条路径都检查返回的 shell。主屏 `0x7662ac` 有创建失败处理。APK 同时包含 Flutter AOT `libapp.so` 和 Rust 入口 `libapp_launcher.so`，库中有 AOT 参数 `--aot-shared-library-name=libapp.so`（`0x28bb9d`）。
2. **绑定 Surface。** 主屏 `request_window`（`0xe1c480 → 0x76391c`）在 `0x763ccc–0x763cdc` 写入 `0xe1d678` 及新分配的窗口状态。attached 槽 `0x777a44` 读取 token 并保留 `WindowOperation` 引用。surface created 槽 `0x7776a4` 保留 `NativeWindow` 引用，在 `0x7776e0 → 0xb9bfb8` 将其转为指针。这里按窗口状态调用 `shell_holder_window_surface_created`（`0xb9c048`，接口 `+0x170 → 0x6ee744`）或 `shell_holder_surface_created`（`0xb9c098`，接口 `+0xa8 → 0x6ea52c`）。多窗口入口额外传窗口 ID，并检查可选接口槽是否存在。次屏的对应回调没有进入这一分支。
3. **回传首帧通知。** 主屏工厂传入的回调表在 `0xf06570 → 0xd447a0` 提供默认窗口回调，在 `0xf065a0 → 0xd44930` 提供按窗口 ID 的回调。两者分别在 `0xd447cc` 和 `0xd44a20` 调 `WindowOperation_first_frame_call`。后一个回调先按窗口 ID 查已登记的 overlay view。[两条回调与清理边界](21-secondary-home-scene-lifecycle.md) 运行库公开包装 `0x70840` 转到私有实现 `0x1bb66c`。后者更新 surface group 的首帧状态，组准备好时在 `0x1bb73c–0x1bb740` 以空事务进入 `report_draw_finished`。该正常通知路径同样可以带空事务，因此 D10 判定超时还依赖紧邻的 `reason=timeout`。buffer 是否已入队需看生产端或 SF 证据。

Flutter 表的绑定由 Launcher 的 `0xf117d8` 导入重定位和 `0xb8891c` 确认。后者最多复制 0x268 字节，Flutter 库导出的 `HYPER_FLUTTER_INTERFACE` 位于 `0x1165c10`，长度 0x280。用表起址加槽偏移，在两库之间对齐间接调用。该 ROM 的次屏类名分支没有构建主屏式宿主的开关，现有证据无法确定其他产品或 ROM 的编译条件，也未确认 Dart AOT 中是否有独立的次屏内容实现。

## [ROM] Buffer 提交与超时完成

- **Buffer 提交。** 正常路径依赖绑定后由 Flutter 的渲染端为该 Surface 生产帧。D10 的 `home-gfxinfo.txt:4–6` 记录同进程管线为 Impeller (Vulkan)。`libhyper_os_flutter.so:0xddd6ac–0xddd6c0` 动态解析 `vkQueuePresentKHR`，`0xe18ec4–0xe18ec8` 有 `AHBSwapchain::Present` 的 trace。库另有 `0x70caf8 → eglSwapBuffers` 的 EGL 路径。现有快照无法区分主屏实际走过的 Vulkan swapchain 子路径，也没有次屏 232/273 的渲染提交事件。运行库的 `WindowOperation.sync_next_transaction` 在 `0x1baac8` 调 `BlastBufferQueue.sync_next_transaction`（`libhyper_os_sys.dylib.so:0xe4620`），用于接收后续事务，调用边的存在只证明运行库提供这一入口。
- **空事务完成。** `WindowController.handle_perform_traversals`（`0x1ae5c4`）在 `0x1ae73c` 构造 `SurfaceSyncGroup`，传入闭包表 `0x238ff0`。表的 `0x239010` 槽经 RELR 指向消费者 `0x18a828`。超时回调 `0x20a81c` 在 `0x20a8a4` 以字符串 `timeout` 调 `mark_sync_ready`（`0x1a59b0`）。后者首次通过就绪检查时，在 `0x1a5a5c` 把事务参数置空，再于 `0x1a5a78` 调消费者。消费者根据参数是否为空生成 `has_tx`，在 `0x18a9c4–0x18a9dc` 仍调用会话的 `+0xb8` 槽，携带窗口、可空事务和序号。匹配的 `BpWindowSession.finishDrawing` 重定位在 AIDL 库 `0xaf5eb0`，目标 `0x8f0c40`，其中 `0x8f0cb4` 序列化可空事务。ROM 的 `WindowStateAnimator.finishDrawingLocked`（本地 JADX `WindowStateAnimator.java:151–182`）可在无事务时进入 `COMMIT_DRAW_PENDING`，只有传入事务才合并。D10 实际日志随后推进到 `HAS_DRAWN`。

**[推测]** 对该 ROM 最有证据支持的解释是，次屏活动建出了系统窗口，却没有通过已定位的生命周期建立窗口专属渲染宿主或复用既有宿主的绑定。这一缺口早于可观测的首帧提交。超时解释了 WM 为何能宣布绘制完成，现有证据未证明它阻止了首帧。两个次屏 VRI 图层均出现在对应外屏层树，普通 Activity 已在同一输出链合成。若之后观察到次屏提交了 buffer，仍需用对应 layer ID 检查 latch、裁剪与可见性。

**[待真机]** 新验证 `NOT_RUN`。如后续另行安排对照，按同一 token、窗口 ID、BufferQueue ID 和 layer ID 记录宿主构建或复用、`NativeWindow` 绑定、首个 buffer 入队与 latch、首帧通知及 WMS 完成。优先用主屏已出帧路径作正对照，且记录回切后的新 layer ID。次屏 Dart 内容、次屏点击至应用启动的调用边仍待查。D9 的电源组和输出刷新率分别沿原路径跟进。

## 复查方法

从 `extracted/native-files.json` 读取 `system_ext` 的已解包路径，Launcher 复用 `analysis/local/inputs/libapp_launcher.so`。用 NDK 30.0.15729638 的 LLVM 21.0.0 执行 `llvm-readelf --dyn-syms --wide`、`-SW` 和 `-rW`，再用 `llvm-objdump -d --start-address=<VA> --stop-address=<VA>` 核对调用点。库的区段索引与本地 objdump 不兼容时，从 ELF `.text` 按 `sh_offset + VA - sh_addr` 取字节，在本地切片保留原 VA 后反汇编。Launcher 表用 RELA addend，UI 消费闭包和 Flutter 接口用 RELR 表地址与该位置的原始 64 位 addend。命名导入用 `.rela.dyn` 或 `.rela.plt` 与 `.dynsym` 交叉核对。所有二进制与反汇编切片留在 `analysis/local/` 或原解包目录。

`python scripts/verify_native_desktop.py --local --d10` 可核对 ROM 库哈希、关键直接分支、RELA/RELR 和归档 D10 的文本及 PNG 哈希。日志按字节换行定位，避免原始 logcat 中的无效 UTF-8 影响行号。可用 Pillow 将两份物理 PNG 转成 RGB，用三通道最大值统计非黑像素，中央区域裁取宽、高的 1/4 到 3/4。截图和日志路径见[证据清单](../analysis/evidence/native-first-frame.json)。
