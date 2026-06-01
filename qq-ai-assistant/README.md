# QQ AI Computer Assistant

基于 [cc-connect](https://github.com/chenhg5/cc-connect) + [NapCatQQ](https://github.com/NapNeko/NapCatQQ) + Claude Code 的 QQ 机器人，带系统托盘管理。

## 功能

- 托盘图标一键启动/停止/重启
- 需要扫码时自动弹出二维码
- 终端实时显示聊天消息
- 右键托盘编辑人设和配置

## 快速开始

### 1. 安装依赖

```bash
npm install -g cc-connect
pip install pystray pillow
```

确保已安装 [Claude Code](https://docs.anthropic.com/claude-code) 和 Python 3.8+。

### 2. 下载 NapCatQQ

从 https://github.com/NapNeko/NapCatQQ/releases 下载 `NapCat.Shell.Windows.OneKey.zip`。

解压后运行 `NapCatInstaller.exe`，完成安装。

将生成的 `NapCat.XXXX.Shell` 目录重命名为 `NapCat.44498.Shell` 放到本项目的 `napcat/` 目录下。

### 3. 配置

```bash
cp config.example.toml config.toml
```

编辑 `config.toml` 填入你的信息：
- `admin_from`：管理员 QQ 号
- `allow_from`：允许使用机器人的 QQ 号
- `work_dir`：你的工作目录
- `system_prompt`：AI 助手人设

然后复制到 cc-connect 目录：

```bash
cp config.toml ~/.cc-connect/config.toml
```

### 4. 编辑人设

编辑 `CLAUDE.md` 写入你的 AI 助手人设和性格。

### 5. 启动

双击 `launcher.bat` 或运行：

```bash
python launcher.py
```

任务栏托盘出现图标，右键操作。

### 6. 扫码登录

首次或 QQ 登录过期时，会自动弹出二维码图片，用手机 QQ 扫码登录。

## 项目结构

```
qq-ai-assistant/
├── launcher.py           # 托盘主程序
├── launcher.bat          # Windows 启动脚本
├── CLAUDE.md             # 人设模板
├── config.example.toml   # 配置模板
├── README.md
└── napcat/               # NapCatQQ（需自行下载）
```

## 技术栈

- [cc-connect](https://github.com/chenhg5/cc-connect) v1.3+
- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) v4.18+
- Claude Code
- Python 3.8+ (pystray, pillow)
