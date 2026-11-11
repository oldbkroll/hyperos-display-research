# 10 MiuiHome 次屏 HOME 生命周期

2026-11-11，`OS4.0.6.0.XPBCNXM`。用同一 ROM 的 Rust UI 运行库解读 MiuiHome 次屏组件的回调表，确认了创建、窗口请求和配置变化的直接路径。应用启动与窗口间接回调的最终目标仍待确认。设备验证 `NOT_RUN`。[回调表与输入哈希](../analysis/evidence/native-desktop-stage2.json)

`libapp_launcher.so` 在组件名匹配后返回 UI 描述符 `0xe1d318`。`libhyper_os_ui_private.dylib.so` 的 `FfiUi` 和 `UiWindow` 导出符号标注了回调名。相应的读取函数从表指针加固定偏移取出目标，结合 Launcher 的 `R_AARCH64_RELATIVE` 重定位可定位具体函数。`request_window` 返回第二个描述符 `0xe1e1f8`，因此窗口回调可以继续按同样方式核对。

| 回调 | 目标地址 | 静态观察 |
|---|---|---|
| `on_create` | `0x776854` | 取 `UiComponentData` token，在日志条件满足时引用 `SecondaryDisplayLauncherUi` 与 `on_create token`，随后释放 `UiComponentData` |
| `on_resume` / `on_destroy` | `0xd49a28` | 直接返回 |
| `on_configuration_changed` / `on_new_intent` | `0x74cbe4` | 直接返回 |
| `request_window` | `0x776834` | 返回窗口描述符 `0xe1e1f8` 及关联数据指针 |
| `on_surface_created` | `0x77a110` | 调用传入对象的间接回调，随后释放 `WindowDisplayInfo` 和 `NativeWindow` 引用。间接回调的目标仍待定位 |
| `on_surface_changed` / `on_window_config_changed` | `0xd49c40` / `0xd49c5c` | 分别释放 `WindowDisplayInfo` 和 `Configuration` |

因此，下一条 native 调查链从 `0x77a130` 的间接调用往上追它的实参来源。应用启动必须找到次屏组件到实际启动调用的可达路径，或在真机核对启动者与目标 `TaskDisplayArea`。目前只有整个库对 `Scene_start_activity` 的导入。主次屏共享状态、显示密度变化的实际效果和重建行为仍需证据。

复查时用 `llvm-readelf --dyn-syms --wide` 读取运行库符号，用 `llvm-readelf -r -W` 读取 Launcher 重定位。原始运行库直接传给本地 `llvm-objdump` 时报告 `invalid section index: 34`。本轮使用只含所选 `.text` 字节的本地 ELF 切片保留虚拟地址，再以原始文件字节校验回调槽位。`python scripts/verify_native_desktop.py --local` 可复查原始输入哈希、九个槽位的取指和重定位目标及直接返回指令。反汇编和切片留在 `analysis/local`。
