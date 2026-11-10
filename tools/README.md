# 本地研究工具

Windows：`python scripts/setup_tools.py`，工具安装到 `tools/bin/`，不修改全局 PATH。

WSL Ubuntu 24.04：`bash scripts/setup_erofs.sh`，deb 解到工作区而非 apt install。

版本、来源、SHA256 见 `analysis/evidence/tools.json`。JADX 的初次下载哈希为本地固定值，不等同于独立签名认证。

运行参数见各脚本、完成标记及 `analysis/local/*.log`。所有工具下载和二进制均排除 Git。

## 已遇到的问题

- `wslpath` 收到 Windows 反斜杠会被 shell 解释；脚本已改为正斜杠绝对路径。
- NanaZip 7.0 直接列 EROFS/AVB 镜像时将内部 ZIP 误识别，报告 Headers Error；未用其结果做文件分析，改用用户态 fsck.erofs。
- JADX 对尚未提取到的 services.jar 首次运行提示 File not found；等待完整文件后重新运行。
- AOSP `DesktopModeStatus.java` 与旧位置 DesktopModeHelper 不适用于该提交；已追踪 import，采用 server/wm/DesktopModeHelper 与 shared/desktopmode/DesktopState。
