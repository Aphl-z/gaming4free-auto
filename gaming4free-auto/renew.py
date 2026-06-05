import os
import sys
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import requests

# 创建截图目录
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def log(message):
    """带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def send_telegram_message(bot_token, chat_id, message):
    """发送 Telegram 消息"""
    if not bot_token or not chat_id:
        log("Telegram 未配置，跳过通知")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            log("Telegram 消息发送成功")
            return True
        else:
            log(f"Telegram 消息发送失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log(f"发送 Telegram 消息时出错: {e}")
        return False

def send_telegram_photo(bot_token, chat_id, photo_path, caption=""):
    """发送 Telegram 图片"""
    if not bot_token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
    except Exception as e:
        log(f"发送 Telegram 图片时出错: {e}")
        return False

async def setup_proxy(context, config):
    """配置代理（如果启用）"""
    proxy_config = config.get("proxy", {})
    if not proxy_config.get("enabled", False):
        return None
    
    proxy_type = proxy_config.get("type", "socks5")
    host = proxy_config.get("host", "127.0.0.1")
    port = proxy_config.get("port", 40000)
    
    proxy_url = f"{proxy_type}://{host}:{port}"
    log(f"使用代理: {proxy_url}")
    return proxy_url

async def renew_server(page, server_config, config, tg_bot_token, tg_chat_id):
    """续期单个服务器"""
    server_name = server_config["name"]
    server_url = server_config["url"]
    username_secret = server_config["username"]
    
    # 从环境变量获取用户名
    username = os.environ.get(username_secret)
    if not username:
        log(f"❌ 错误: 未找到环境变量 {username_secret}")
        return False
    
    log(f"开始续期服务器: {server_name} ({server_url})")
    
    try:
        # 访问服务器页面
        log(f"正在访问 {server_url}")
        await page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        # 保存初始截图
        screenshot_path = SCREENSHOT_DIR / f"{server_name}_01_initial.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        log(f"保存截图: {screenshot_path}")
        
        # 等待用户名输入框
        log("等待用户名输入框...")
        username_input = await page.wait_for_selector('input[name="username"]', timeout=15000)
        await username_input.fill(username)
        log(f"已填入用户名: {username}")
        
        # 保存填入用户名后的截图
        screenshot_path = SCREENSHOT_DIR / f"{server_name}_02_username_filled.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        
        # 点击 Turnstile 验证框
        turnstile_config = config.get("turnstile", {})
        click_x = turnstile_config.get("click_x", 640)
        click_y = turnstile_config.get("click_y", 405)
        
        log(f"点击 Turnstile 验证框 ({click_x}, {click_y})")
        await page.mouse.click(click_x, click_y)
        await asyncio.sleep(5)
        
        # 保存点击验证框后的截图
        screenshot_path = SCREENSHOT_DIR / f"{server_name}_03_turnstile_clicked.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        
        # 等待并点击续期按钮
        log("等待续期按钮...")
        renew_button = await page.wait_for_selector('button:has-text("renew")', timeout=15000)
        await renew_button.click()
        log("已点击续期按钮")
        await asyncio.sleep(3)
        
        # 保存最终截图
        screenshot_path = SCREENSHOT_DIR / f"{server_name}_04_final.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        
        # 检查是否成功
        page_content = await page.content()
        if "success" in page_content.lower() or "renewed" in page_content.lower():
            log(f"✅ 服务器 {server_name} 续期成功！")
            message = f"✅ *续期成功*\n\n服务器: `{server_name}`\n时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            send_telegram_message(tg_bot_token, tg_chat_id, message)
            return True
        else:
            log(f"⚠️ 服务器 {server_name} 续期状态未知")
            message = f"⚠️ *续期状态未知*\n\n服务器: `{server_name}`\n时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n请检查截图"
            send_telegram_message(tg_bot_token, tg_chat_id, message)
            send_telegram_photo(tg_bot_token, tg_chat_id, str(screenshot_path), f"{server_name} - 最终状态")
            return False
            
    except Exception as e:
        log(f"❌ 服务器 {server_name} 续期失败: {e}")
        
        # 保存错误截图
        try:
            screenshot_path = SCREENSHOT_DIR / f"{server_name}_error.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            message = f"❌ *续期失败*\n\n服务器: `{server_name}`\n时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n错误: `{str(e)[:200]}`"
            send_telegram_message(tg_bot_token, tg_chat_id, message)
            send_telegram_photo(tg_bot_token, tg_chat_id, str(screenshot_path), f"{server_name} - 错误截图")
        except:
            pass
        
        return False

async def main():
    """主函数"""
    log("=" * 60)
    log("Gaming4Free 自动续期脚本启动")
    log("=" * 60)
    
    # 读取配置文件
    config_path = Path("config.json")
    if not config_path.exists():
        log("❌ 错误: 未找到 config.json")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 获取 Telegram 配置
    tg_config = config.get("telegram", {})
    tg_enabled = tg_config.get("enabled", False)
    tg_bot_token = os.environ.get(tg_config.get("bot_token_secret", "")) if tg_enabled else None
    tg_chat_id = os.environ.get(tg_config.get("chat_id_secret", "")) if tg_enabled else None
    
    if tg_enabled and (not tg_bot_token or not tg_chat_id):
        log("⚠️ 警告: Telegram 已启用但凭据不完整，将跳过通知")
        tg_enabled = False
    
    # 启动 Playwright
    async with async_playwright() as p:
        # 配置代理
        proxy_config = config.get("proxy", {})
        browser_args = {}
        if proxy_config.get("enabled", False):
            proxy_url = f"{proxy_config['type']}://{proxy_config['host']}:{proxy_config['port']}"
            browser_args["proxy"] = {"server": proxy_url}
            log(f"使用代理: {proxy_url}")
        
        # 启动浏览器
        browser = await p.chromium.launch(headless=True, **browser_args)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 处理每个服务器
        servers = config.get("servers", [])
        success_count = 0
        fail_count = 0
        
        for server in servers:
            try:
                result = await renew_server(page, server, config, tg_bot_token, tg_chat_id)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                log(f"处理服务器 {server['name']} 时出错: {e}")
                fail_count += 1
            
            # 服务器之间等待一段时间
            await asyncio.sleep(5)
        
        await browser.close()
    
    log("=" * 60)
    log(f"续期完成: 成功 {success_count}，失败 {fail_count}")
    log("=" * 60)
    
    # 发送总结消息
    if tg_enabled:
        summary = f"📊 *续期总结*\n\n✅ 成功: {success_count}\n❌ 失败: {fail_count}\n⏰ 时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        send_telegram_message(tg_bot_token, tg_chat_id, summary)
    
    # 如果有失败，退出码为 1
    if fail_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
