# Gaming4Free 自动续期

自动续期 Gaming4Free 服务器的 GitHub Actions 工作流。

## 功能

- ✅ 支持多服务器自动续期
- ✅ 自动处理 Cloudflare Turnstile 验证
- ✅ Telegram 通知（成功/失败）
- ✅ 自动截图保存
- ✅ 支持 SOCKS5 代理
- ✅ 每小时自动运行

## 配置

### 1. GitHub Secrets

在仓库的 Settings → Secrets and variables → Actions 中添加以下 secrets：

- `MC_USERNAME`: 第一台服务器的用户名
- `MC_USERNAME_2`: 第二台服务器的用户名
- `TG_BOT_TOKEN`: Telegram Bot Token（可选）
- `TG_CHAT_ID`: Telegram Chat ID（可选）

### 2. 配置文件

`config.json` 包含服务器和代理配置：

```json
{
  "servers": [
    {
      "name": "Nass",
      "url": "https://g4f.gg/ads",
      "username": "MC_USERNAME"
    },
    {
      "name": "lucky-va",
      "url": "https://asd-2.g4f.gg",
      "username": "MC_USERNAME_2"
    }
  ],
  "turnstile": {
    "click_x": 640,
    "click_y": 405
  },
  "proxy": {
    "enabled": true,
    "type": "socks5",
    "host": "127.0.0.1",
    "port": 40000
  },
  "telegram": {
    "enabled": true,
    "bot_token_secret": "TG_BOT_TOKEN",
    "chat_id_secret": "TG_CHAT_ID"
  }
}
```

## 使用

### 自动运行

工作流会在每小时的第 40 分钟自动运行。

### 手动触发

1. 进入仓库的 Actions 页面
2. 选择 "自动续期服务器" 工作流
3. 点击 "Run workflow"

## 故障排除

如果续期失败，检查：

1. GitHub Actions 日志
2. 下载的截图 artifacts
3. 用户名是否正确
4. 服务器 URL 是否可访问

## 技术栈

- Python 3.10
- Playwright（浏览器自动化）
- Telegram Bot API（通知）
