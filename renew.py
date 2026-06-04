import os, sys, time, urllib.request, json, traceback
from seleniumbase import SB

# ==========================================
# G4F.GG 自动续期 (修复版 - TG通知可追踪)
# ==========================================
TARGET_URL = "https://g4f.gg/renqi" 

# 多账户支持
ACCOUNTS = []
if os.getenv("MC_USERNAME"):
    ACCOUNTS.append(os.getenv("MC_USERNAME"))
if os.getenv("MC_USERNAME_2"):
    ACCOUNTS.append(os.getenv("MC_USERNAME_2"))

if not ACCOUNTS:
    print("[ERROR] 未配置任何账户！请设置 MC_USERNAME 和/或 MC_USERNAME_2 Secret")
    sys.exit(1)

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")

print(f"[TG] Token 长度: {len(TG_TOKEN)} (掩码: {TG_TOKEN[:8]}*** 如为0则未配置)")
print(f"[TG] Chat ID: {TG_CHAT}")

def send_tg(msg):
    """发送 Telegram 通知，失败时打印详细错误"""
    if not TG_TOKEN or not TG_CHAT:
        print(f"[TG] 跳过发送 - Token或Chat ID未配置 (token_len={len(TG_TOKEN)}, chat={TG_CHAT})")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TG_CHAT,
            "text": f"G4F 自动续期:\n{msg}",
            "parse_mode": "HTML"
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print(f"[TG] 消息发送成功 -> chat_id={TG_CHAT}")
                return True
            else:
                print(f"[TG] 发送失败! API返回: {result}")
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[TG] HTTP错误 {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[TG] 发送异常: {e}")
        traceback.print_exc()
        return False

print(f"\n===== 开始执行极速续期 (G4F.GG) =====")
print(f"账户列表: {ACCOUNTS}")
print(f"账户数量: {len(ACCOUNTS)}\n")

proxy_str = "socks5://127.0.0.1:40000"

for idx, MC_USERNAME in enumerate(ACCOUNTS, 1):
    print(f"\n{'='*60}")
    print(f"[{idx}/{len(ACCOUNTS)}] 正在处理账户: {MC_USERNAME}")
    print(f"{'='*60}\n")
    
    try:
        with SB(uc=True, proxy=proxy_str, headless=False, window_size="1920,1080") as sb:
            if idx == 1:
                print("安装 xdotool...")
                os.system("sudo apt-get update -qq > /dev/null 2>&1")
                os.system("sudo apt-get install -y -qq xdotool > /dev/null 2>&1")

            print(f"访问: {TARGET_URL}")
            sb.open(TARGET_URL)
            sb.sleep(6) 
            
            os.makedirs("screenshots", exist_ok=True)
            sb.save_screenshot(f"screenshots/{MC_USERNAME}_1_page_loaded.png")

            print("填入游戏ID...")
            try:
                sb.type('input[placeholder*="Steve"], input[placeholder*="Player"]', MC_USERNAME, timeout=4)
                print("[OK] ID 填入成功")
            except:
                print("[INFO] 未找到输入框或无需填入，继续")

            print("触发 [+ ADD 90 MIN] 按钮...")
            js_click_code = """
            let els = document.querySelectorAll('button, a, input, div, span');
            for (let i = els.length - 1; i >= 0; i--) {
                let el = els[i];
                let text = (el.innerText || el.value || '').toUpperCase();
                if (text.includes('ADD 90')) {
                    el.click();
                    break;
                }
            }
            """
            sb.execute_script(js_click_code)
            try:
                sb.click('xpath=//*[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "add 90")]', timeout=2)
            except:
                pass

            print("等待 6 秒 CF 盾展开...")
            time.sleep(6) 
            
            print("穿甲雷达扫描 Shadow DOM...")
            js_radar = """
        (function() {
            function getIframe(root) {
                let iframes = root.querySelectorAll('iframe');
                for(let f of iframes) {
                    let s = (f.src || '').toLowerCase();
                    if(s.includes('cloudflare') || s.includes('turnstile')) return f;
                }
                let all = root.querySelectorAll('*');
                for(let el of all) {
                    if(el.shadowRoot) {
                        let found = getIframe(el.shadowRoot);
                        if(found) return found;
                    }
                }
                return null;
            }
            let cf = getIframe(document);
            if (cf) {
                let rect = cf.getBoundingClientRect();
                let ui_y = 85; 
                let target_x = rect.left + 30;
                let target_y = rect.top + ui_y + (rect.height / 2);
                document.body.setAttribute('data-cf-coords', Math.round(target_x) + ',' + Math.round(target_y));
            } else {
                document.body.setAttribute('data-cf-coords', 'NOT_FOUND');
            }
            })();
            """
            sb.execute_script(js_radar)
        
            coords = None
            try:
                coords = sb.get_attribute("body", "data-cf-coords")
            except:
                pass
        
            if coords and coords != "NOT_FOUND":
                target_x, target_y = coords.split(",")
                print(f"[RADAR] CF 盾坐标: ({target_x}, {target_y})")
            else:
                print("[RADAR] 未找到 iframe，使用黄金盲狙坐标")
                target_x, target_y = "640", "405"
                print(f"[RADAR] 黄金坐标: ({target_x}, {target_y})")

            print("物理鼠标点击 Turnstile...")
            os.system(f"xdotool mousemove {target_x} {target_y} click 1")
        
            print("等待 8 秒 Turnstile 验证...")
            time.sleep(8)
            
            try:
                sb.save_screenshot(f"screenshots/{MC_USERNAME}_2_result.png")
                print("[OK] 最终截图已保存")
            except:
                print("[WARN] 截图保存失败")

            print("[OK] 流程执行完毕")
            send_tg(f"[OK] 服务器 [{MC_USERNAME}] 续期脚本运行完毕!\n破盾方式: 双重核武物理盲狙\n请查阅 GitHub Actions Artifact 截图确认战果")

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        send_tg(f"[FAIL] 账户 [{MC_USERNAME}] 自动续期崩溃: {e}")

print(f"\n{'='*60}")
print(f"所有账户处理完成! 共处理 {len(ACCOUNTS)} 个账户")
print(f"{'='*60}\n")

# 发送汇总通知 (如果配置了TG)
if len(ACCOUNTS) >= 1:
    send_tg(f"G4F 续期批次完成 - 共处理 {len(ACCOUNTS)} 个账户: {', '.join(ACCOUNTS)}")
