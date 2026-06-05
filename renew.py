import os, sys, time, urllib.request, json, traceback
from seleniumbase import SB

# ==========================================
# G4F.GG 多服务器自动续期
# ==========================================

# 服务器列表：每个服务器有独立页面 https://g4f.gg/{slug}
SERVERS = []
if os.getenv("MC_USERNAME"):
    SERVERS.append(os.getenv("MC_USERNAME"))
if os.getenv("MC_USERNAME_2"):
    SERVERS.append(os.getenv("MC_USERNAME_2"))

if not SERVERS:
    print("[ERROR] No servers configured!")
    sys.exit(1)

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        print(f"[TG] Skip - no config")
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TG_CHAT, "text": f"G4F: {msg}"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print(f"[TG] Sent OK")
                return True
            else:
                print(f"[TG] FAIL: {result}")
                return False
    except Exception as e:
        print(f"[TG] Error: {e}")
        return False

print(f"TG Token len: {len(TG_TOKEN)}, Chat ID: {TG_CHAT}")
print(f"Servers: {SERVERS}")
print(f"Total: {len(SERVERS)}")

proxy_str = "socks5://127.0.0.1:40000"

for idx, SERVER_SLUG in enumerate(SERVERS, 1):
    TARGET_URL = f"https://g4f.gg/{SERVER_SLUG}"
    print(f"\n{'='*60}")
    print(f"[{idx}/{len(SERVERS)}] Server: {SERVER_SLUG} -> {TARGET_URL}")
    print(f"{'='*60}")
    
    try:
        with SB(uc=True, proxy=proxy_str, headless=False, window_size="1920,1080") as sb:
            if idx == 1:
                print("Setup xdotool...")
                os.system("sudo apt-get update -qq > /dev/null 2>&1")
                os.system("sudo apt-get install -y -qq xdotool > /dev/null 2>&1")
            
            print(f"Opening: {TARGET_URL}")
            sb.open(TARGET_URL)
            sb.sleep(5)
            
            os.makedirs("screenshots", exist_ok=True)
            sb.save_screenshot(f"screenshots/{SERVER_SLUG}_1_loaded.png")
            print("[OK] Page loaded")

            # Click ADD 90 MIN button
            print("Clicking [+ ADD 90 MIN]...")
            js = """
            let els = document.querySelectorAll('button, a, input, div, span');
            for(let el of els) {
                let t = (el.innerText || el.value || '').toUpperCase();
                if(t.includes('ADD 90')) { el.click(); break; }
            }
            """
            sb.execute_script(js)
            try:
                sb.click('xpath=//*[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "add 90")]', timeout=2)
            except:
                pass
            
            print("Wait 6s for CF Turnstile...")
            time.sleep(6)
            
            # Radar for CF iframe
            print("Shadow DOM radar...")
            js_radar = """
            (function() {
                function gf(root) {
                    let ifs = root.querySelectorAll('iframe');
                    for(let f of ifs) {
                        let s = (f.src || '').toLowerCase();
                        if(s.includes('cloudflare') || s.includes('turnstile')) return f;
                    }
                    let all = root.querySelectorAll('*');
                    for(let el of all) {
                        if(el.shadowRoot) {
                            let found = gf(el.shadowRoot);
                            if(found) return found;
                        }
                    }
                    return null;
                }
                let cf = gf(document);
                if(cf) {
                    let r = cf.getBoundingClientRect();
                    document.body.setAttribute('data-cf', Math.round(r.left+30)+','+Math.round(r.top+85+r.height/2));
                } else {
                    document.body.setAttribute('data-cf', 'NF');
                }
            })();
            """
            sb.execute_script(js_radar)
            
            coords = sb.get_attribute("body", "data-cf") or "NF"
            if coords != "NF":
                tx, ty = coords.split(",")
                print(f"[RADAR] CF target: ({tx}, {ty})")
            else:
                tx, ty = "640", "405"
                print(f"[RADAR] Fallback coords: ({tx}, {ty})")
            
            print("xdotool click...")
            os.system(f"xdotool mousemove {tx} {ty} click 1")
            
            print("Wait 8s for verification...")
            time.sleep(8)
            
            sb.save_screenshot(f"screenshots/{SERVER_SLUG}_2_result.png")
            print(f"[OK] {SERVER_SLUG} done!")
            send_tg(f"[OK] {SERVER_SLUG} +90min")
            
    except Exception as e:
        print(f"[FAIL] {SERVER_SLUG}: {e}")
        traceback.print_exc()
        send_tg(f"[FAIL] {SERVER_SLUG}: {e}")

print(f"\nDone! {len(SERVERS)} servers processed.")
