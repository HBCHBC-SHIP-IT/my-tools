# DeepSeek 余额桌面挂件

一个终端风格的桌面小挂件，实时显示 DeepSeek API 余额。

## 截图

```
╔══════════════════════════╗
║ ● ● ● deepseek-monitor ⚙║
║──────────────────────────║
║ $ balance                ║
║ ¥12.34                   ║
║   ↓ ¥0.0123              ║
║                          ║
║ $ detail                 ║
║ topped_up  ¥20.00        ║
║ granted    ¥0.50         ║
║──────────────────────────║
║ ⬤ online         14:30:00║
╚══════════════════════════╝
```

## 功能

- 📊 实时显示 DeepSeek API 余额、充值金额、赠送金额
- 📈 与上次查询对比，显示余额变化
- 🖱️ 可拖拽、始终置顶
- 🔽 双击任意位置最小化，双击小按钮恢复
- ⚙️ 点击齿轮图标设置 API Key
- 🟢 代理可用时走代理，不可用时自动直连

## 使用方法

```bash
# 安装依赖：无需额外依赖，仅需 Python 3 和 curl

# 后台运行（无终端窗口）
pythonw deepseek_widget.py

# 或前台运行（会显示终端）
python deepseek_widget.py
```

首次运行会显示 "no key"，点击右上角齿轮图标输入你的 DeepSeek API Key 即可。

## 代理说明

挂件自动读取 `HTTPS_PROXY` 环境变量：如果 socks5 代理端口可连接就使用代理，否则直连。适合间歇性使用 v2ray/Radmin VPN 的用户。

## 配置存储

API Key 保存在 `~/.deepseek_widget_config.json`，不上传 GitHub。
