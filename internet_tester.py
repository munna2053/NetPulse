import json
import socket
import ssl
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
TCP_TIMEOUT = 4.0
TLS_TIMEOUT = 3.0

T = [
    ("google", "Google", "Search", "N. America", "US", "google.com"),
    ("bing", "Bing", "Search", "N. America", "US", "bing.com"),
    ("duckduckgo", "DuckDuckGo", "Search", "N. America", "US", "duckduckgo.com"),
    ("yandex", "Yandex", "Search", "Europe", "RU", "yandex.com"),
    ("baidu", "Baidu", "Search", "Asia", "CN", "baidu.com"),
    ("naver", "Naver", "Search", "Asia", "KR", "naver.com"),

    ("facebook", "Facebook", "Social", "N. America", "US", "facebook.com"),
    ("instagram", "Instagram", "Social", "N. America", "US", "instagram.com"),
    ("x", "X (Twitter)", "Social", "N. America", "US", "x.com"),
    ("reddit", "Reddit", "Social", "N. America", "US", "reddit.com"),
    ("linkedin", "LinkedIn", "Social", "N. America", "US", "linkedin.com"),
    ("tiktok", "TikTok", "Social", "Asia", "SG", "tiktok.com"),
    ("vk", "VK", "Social", "Europe", "RU", "vk.com"),

    ("youtube", "YouTube", "Streaming", "N. America", "US", "youtube.com"),
    ("netflix", "Netflix", "Streaming", "N. America", "US", "netflix.com"),
    ("twitch", "Twitch", "Streaming", "N. America", "US", "twitch.tv"),
    ("disneyplus", "Disney+", "Streaming", "N. America", "US", "disneyplus.com"),
    ("primevideo", "Prime Video", "Streaming", "N. America", "US", "primevideo.com"),
    ("bilibili", "Bilibili", "Streaming", "Asia", "CN", "bilibili.com"),
    ("spotify", "Spotify", "Streaming", "Europe", "SE", "spotify.com"),
    ("soundcloud", "SoundCloud", "Streaming", "Europe", "DE", "soundcloud.com"),

    ("chatgpt", "ChatGPT", "AI", "N. America", "US", "chatgpt.com"),
    ("claude", "Claude", "AI", "N. America", "US", "claude.ai"),
    ("gemini", "Gemini", "AI", "N. America", "US", "gemini.google.com"),
    ("huggingface", "Hugging Face", "AI", "N. America", "US", "huggingface.co"),
    ("deepseek", "DeepSeek", "AI", "Asia", "CN", "deepseek.com"),
    ("mistral", "Mistral AI", "AI", "Europe", "FR", "mistral.ai"),

    ("github", "GitHub", "Cloud & Dev", "N. America", "US", "github.com"),
    ("gitlab", "GitLab", "Cloud & Dev", "N. America", "US", "gitlab.com"),
    ("stackoverflow", "Stack Overflow", "Cloud & Dev", "N. America", "US", "stackoverflow.com"),
    ("cloudflare", "Cloudflare", "Cloud & Dev", "N. America", "US", "cloudflare.com"),
    ("aws", "Amazon AWS", "Cloud & Dev", "N. America", "US", "aws.amazon.com"),
    ("azure", "Microsoft Azure", "Cloud & Dev", "N. America", "US", "azure.microsoft.com"),
    ("vercel", "Vercel", "Cloud & Dev", "N. America", "US", "vercel.com"),
    ("canva", "Canva", "Cloud & Dev", "Oceania", "AU", "canva.com"),

    ("bbc", "BBC News", "News", "Europe", "GB", "bbc.com"),
    ("cnn", "CNN", "News", "N. America", "US", "cnn.com"),
    ("reuters", "Reuters", "News", "N. America", "US", "reuters.com"),
    ("aljazeera", "Al Jazeera", "News", "Middle East", "QA", "aljazeera.com"),
    ("dw", "Deutsche Welle", "News", "Europe", "DE", "dw.com"),
    ("lemonde", "Le Monde", "News", "Europe", "FR", "lemonde.fr"),
    ("timesofindia", "Times of India", "News", "Asia", "IN", "timesofindia.indiatimes.com"),
    ("globo", "Globo", "News", "S. America", "BR", "globo.com"),
    ("abcnewsau", "ABC News AU", "News", "Oceania", "AU", "abc.net.au"),
    ("stuffnz", "Stuff NZ", "News", "Oceania", "NZ", "stuff.co.nz"),

    ("amazon", "Amazon", "Shopping", "N. America", "US", "amazon.com"),
    ("ebay", "eBay", "Shopping", "N. America", "US", "ebay.com"),
    ("aliexpress", "AliExpress", "Shopping", "Asia", "CN", "aliexpress.com"),
    ("flipkart", "Flipkart", "Shopping", "Asia", "IN", "flipkart.com"),
    ("mercadolibre", "Mercado Libre", "Shopping", "S. America", "AR", "mercadolibre.com"),
    ("rakuten", "Rakuten", "Shopping", "Asia", "JP", "rakuten.com"),
    ("takealot", "Takealot", "Shopping", "Africa", "ZA", "takealot.com"),

    ("whatsapp", "WhatsApp", "Messaging", "N. America", "US", "whatsapp.com"),
    ("telegram", "Telegram", "Messaging", "Middle East", "AE", "telegram.org"),
    ("discord", "Discord", "Messaging", "N. America", "US", "discord.com"),
    ("slack", "Slack", "Messaging", "N. America", "US", "slack.com"),
    ("zoom", "Zoom", "Messaging", "N. America", "US", "zoom.us"),
    ("signal", "Signal", "Messaging", "N. America", "US", "signal.org"),
]

TARGETS = [
    {"id": idx, "name": n, "cat": c, "region": r, "cc": cc, "host": h}
    for idx, (key, n, c, r, cc, h) in enumerate(T)
]
BY_ID = {t["id"]: t for t in TARGETS}

_network_cache = {"list": [], "ts": 0.0}
_network_lock = threading.Lock()


def _ps_json(cmd):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(out.stdout) if out.stdout.strip() else []
    except Exception:
        return []


def get_networks(force=False):
    with _network_lock:
        now = time.time()
        if not force and _network_cache["list"] and now - _network_cache["ts"] < 30:
            return _network_cache["list"]
        nets = []
        rows = _ps_json(
            "Get-NetIPConfiguration | Where-Object { $_.IPv4Address } | "
            "ForEach-Object { [pscustomobject]@{ alias=$_.InterfaceAlias; "
            "ip=($_.IPv4Address | Select-Object -First 1).IPAddress; "
            "desc=[string]$_.InterfaceDescription; "
            "gw=[string]($_.IPv4DefaultGateway | Select-Object -First 1).NextHop } } "
            "| ConvertTo-Json -Compress"
        )
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            ip = row.get("ip")
            if not ip or ip.startswith("169.254.") or ip.startswith("127."):
                continue
            nets.append({
                "alias": row.get("alias") or "Network",
                "desc": row.get("desc") or "",
                "ip": ip,
                "gw": row.get("gw") or "",
                "online": bool(row.get("gw")),
            })
        if not nets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except OSError:
                ip = ""
            nets.append({"alias": "Default", "desc": "System default route",
                         "ip": ip, "gw": "", "online": True})
        _network_cache["list"] = nets
        _network_cache["ts"] = now
        return nets


def resolve_src_ip(net_index):
    nets = get_networks()
    if net_index is not None and 0 <= net_index < len(nets):
        ip = nets[net_index]["ip"]
        return ip or None
    return None


def run_test(t, src_ip=None):
    host = t["host"]
    res = {
        "id": t["id"], "ok": False, "ms": None,
        "status": None, "error": None,
    }
    sock = None
    try:
        t0 = time.perf_counter()
        if src_ip:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((src_ip, 0))
            sock.settimeout(TCP_TIMEOUT)
            sock.connect((host, 443))
        else:
            sock = socket.create_connection((host, 443), timeout=TCP_TIMEOUT)
        res["ms"] = round((time.perf_counter() - t0) * 1000)
        res["ok"] = True
        try:
            sock.settimeout(TLS_TIMEOUT)
            ctx = ssl.create_default_context()
            tls = ctx.wrap_socket(sock, server_hostname=host)
            req = (
                f"HEAD / HTTP/1.1\r\nHost: {host}\r\n"
                "User-Agent: NetPulse/1.0\r\nConnection: close\r\n\r\n"
            ).encode()
            tls.sendall(req)
            first = b""
            while b"\r\n" not in first:
                chunk = tls.recv(64)
                if not chunk:
                    break
                first += chunk
                if len(first) > 256:
                    break
            line = first.split(b"\r\n", 1)[0].decode("latin-1", "ignore")
            parts = line.split(" ")
            if len(parts) >= 2 and parts[0].startswith("HTTP"):
                res["status"] = int(parts[1])
        except Exception:
            pass
        return res
    except socket.gaierror:
        res["error"] = "DNS lookup failed"
        return res
    except socket.timeout:
        res["error"] = "Timed out"
        return res
    except (ConnectionRefusedError, ConnectionResetError):
        res["error"] = "Connection refused"
        return res
    except OSError as e:
        res["error"] = str(e) or "Network error"
        return res
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NetPulse — Global Internet Tester</title>
<style>
:root{
  --bg:#070b14; --card:rgba(255,255,255,.045); --border:rgba(255,255,255,.09);
  --txt:#e8ecf6; --dim:#8a93a8; --acc1:#6366f1; --acc2:#22d3ee;
  --good:#34d399; --mid:#fbbf24; --slow:#fb923c; --bad:#f87171;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scrollbar-color:#2a3350 var(--bg)}
body{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  background:var(--bg); color:var(--txt); min-height:100vh; overflow-x:hidden;
}
.bg-blob{position:fixed;border-radius:50%;filter:blur(110px);opacity:.28;z-index:0;pointer-events:none}
.b1{width:520px;height:520px;background:#4338ca;top:-160px;left:-120px;animation:drift 16s ease-in-out infinite alternate}
.b2{width:460px;height:460px;background:#0891b2;bottom:-140px;right:-100px;animation:drift 19s ease-in-out infinite alternate-reverse}
@keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(70px,50px) scale(1.15)}}
.wrap{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding:28px 24px 60px}

#progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:50;
  background:linear-gradient(90deg,var(--acc1),var(--acc2));
  box-shadow:0 0 12px rgba(99,102,241,.9);transition:width .25s ease}

header{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:26px}
.logo{display:flex;align-items:center;gap:14px;margin-right:auto}
.logo .mark{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--acc1),var(--acc2));box-shadow:0 6px 24px rgba(99,102,241,.45)}
h1{font-size:1.55rem;letter-spacing:.5px;background:linear-gradient(90deg,#fff,#a5b4fc);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.tagline{color:var(--dim);font-size:.82rem;margin-top:2px}

.gauge{position:relative;width:92px;height:92px;flex:none}
.gauge svg{transform:rotate(-90deg)}
.gauge .track{fill:none;stroke:rgba(255,255,255,.08);stroke-width:7}
.gauge .val{fill:none;stroke:url(#grad);stroke-width:7;stroke-linecap:round;
  stroke-dasharray:264;stroke-dashoffset:264;transition:stroke-dashoffset 1s ease,stroke .5s}
.gauge .num{position:absolute;inset:0;display:grid;place-content:center;text-align:center}
.gauge .num b{font-size:1.35rem}
.gauge .num span{font-size:.58rem;color:var(--dim);letter-spacing:1.5px;text-transform:uppercase}

#startBtn{
  padding:13px 30px;border:none;border-radius:999px;cursor:pointer;font-size:1rem;font-weight:700;color:#fff;
  background:linear-gradient(135deg,var(--acc1),var(--acc2));font-family:inherit;
  transition:transform .15s,box-shadow .3s;box-shadow:0 6px 22px rgba(79,70,229,.5);
}
#startBtn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 10px 30px rgba(34,211,238,.45)}
#startBtn:disabled{opacity:.55;cursor:not-allowed}
#startBtn.running{animation:pulse 1.6s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,.55)}50%{box-shadow:0 0 0 14px rgba(99,102,241,0)}}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 18px;backdrop-filter:blur(12px)}
.stat .lbl{color:var(--dim);font-size:.72rem;text-transform:uppercase;letter-spacing:1.2px;display:flex;gap:7px;align-items:center;margin-bottom:8px}
.stat .val{font-size:1.35rem;font-weight:700}
.stat .sub{font-size:.75rem;color:var(--dim);margin-top:3px}

.filters{display:flex;flex-direction:column;gap:10px;margin-bottom:22px}
.chiprow{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chiprow .rlbl{font-size:.72rem;color:var(--dim);text-transform:uppercase;letter-spacing:1.2px;width:52px;flex:none}
.chip{
  padding:7px 15px;border-radius:999px;font-size:.82rem;cursor:pointer;color:var(--dim);
  background:var(--card);border:1px solid var(--border);transition:all .18s;user-select:none;font-family:inherit;
}
.chip:hover{color:var(--txt);border-color:rgba(255,255,255,.25)}
.chip.on{background:linear-gradient(135deg,var(--acc1),var(--acc2));color:#fff;border-color:transparent;box-shadow:0 4px 16px rgba(79,70,229,.4)}

#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:14px}
.card{
  background:var(--card);border:1px solid var(--border);border-radius:17px;padding:15px 16px 13px;
  backdrop-filter:blur(12px);transition:transform .18s,border-color .18s,box-shadow .18s;position:relative;
}
.card:hover{transform:translateY(-3px);border-color:rgba(129,140,248,.5);box-shadow:0 12px 32px rgba(0,0,0,.35)}
.card.hidden{display:none}
.card.testing{border-color:rgba(251,191,36,.45)}
.card.ok{border-left:3px solid var(--good)}
.card.fail{border-left:3px solid var(--bad)}
.c-top{display:flex;align-items:center;gap:9px}
.flag{font-size:1.05rem}
.c-name{font-weight:600;font-size:.93rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{margin-left:auto;width:9px;height:9px;border-radius:50%;background:#4b5563;flex:none}
.dot.testing{background:var(--mid);animation:blink 1s ease-in-out infinite}
.dot.ok{background:var(--good);box-shadow:0 0 9px rgba(52,211,153,.8)}
.dot.fail{background:var(--bad);box-shadow:0 0 9px rgba(248,113,113,.8)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.c-meta{display:flex;gap:6px;margin:8px 0 10px}
.badge{font-size:.62rem;padding:3px 8px;border-radius:6px;letter-spacing:.4px;font-weight:600}
.badge.cat{background:rgba(99,102,241,.16);color:#a5b4fc}
.badge.reg{background:rgba(255,255,255,.07);color:var(--dim)}
.ms-line{display:flex;align-items:baseline;gap:6px}
.ms{font-size:1.5rem;font-weight:800;font-variant-numeric:tabular-nums}
.unit{font-size:.72rem;color:var(--dim)}
.http{font-size:.68rem;color:var(--dim);margin-left:auto}
.bar{height:5px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden;margin:9px 0 8px}
.bar i{display:block;height:100%;width:0;border-radius:99px;background:var(--good);transition:width .6s ease,background .4s}
.state{font-size:.72rem;color:var(--dim)}
.retry{
  position:absolute;top:11px;right:40px;width:24px;height:24px;border-radius:8px;border:1px solid var(--border);
  background:rgba(0,0,0,.25);color:var(--dim);cursor:pointer;font-size:.8rem;line-height:1;display:none;place-items:center;font-family:inherit;
}
.card:hover .retry{display:grid}
.retry:hover{color:#fff;border-color:var(--acc1)}

.netbox{display:flex;align-items:center;gap:9px;background:var(--card);border:1px solid var(--border);
  border-radius:999px;padding:8px 14px;backdrop-filter:blur(12px)}
.netbox .nicon{font-size:.95rem}
.netbox select{background:transparent;border:none;color:var(--txt);font-family:inherit;font-size:.85rem;
  cursor:pointer;outline:none;max-width:230px;font-weight:600}
.netbox select option{background:#11162a;color:#e8ecf6}
.netbox select:disabled{opacity:.6}
#netRefresh{width:26px;height:26px;border-radius:50%;border:1px solid var(--border);background:rgba(0,0,0,.25);
  color:var(--dim);cursor:pointer;font-size:.75rem;line-height:1}
#netRefresh:hover{color:#fff;border-color:var(--acc1)}
#reportBtn{padding:13px 22px;border-radius:999px;cursor:pointer;font-weight:700;font-size:.95rem;
  font-family:inherit;color:var(--txt);background:var(--card);border:1px solid var(--border);
  backdrop-filter:blur(12px);transition:all .18s}
#reportBtn:hover:not(:disabled){border-color:var(--acc2);transform:translateY(-2px);color:#fff;
  box-shadow:0 8px 24px rgba(34,211,238,.25)}
#reportBtn:disabled{opacity:.4;cursor:not-allowed}

footer{margin-top:34px;text-align:center;color:var(--dim);font-size:.75rem;line-height:1.7}
footer b{color:#a5b4fc}
@media(max-width:640px){header{justify-content:center}.logo{width:100%;justify-content:center}}
</style>
</head>
<body>
<div id="progress"></div>
<div class="bg-blob b1"></div><div class="bg-blob b2"></div>
<div class="wrap">
<header>
  <div class="logo">
    <div class="mark"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M2 12h4l3-8 4 16 3-8h6"/></svg></div>
    <div><h1>NetPulse</h1><div class="tagline">Global Internet Connectivity Tester</div></div>
  </div>
  <div class="netbox" id="netBox" style="display:none" title="Choose which network adapter to test through">
    <span class="nicon">📡</span>
    <select id="netSel"></select>
    <button id="netRefresh" title="Re-scan network adapters">↻</button>
  </div>
  <div class="gauge">
    <svg width="92" height="92"><defs><linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs><circle class="track" cx="46" cy="46" r="42"/><circle class="val" id="ring" cx="46" cy="46" r="42"/></svg>
    <div class="num"><b id="score">—</b><span>score</span></div>
  </div>
  <button id="reportBtn" disabled title="Download the last test as a shareable HTML report">⬇ Report</button>
  <button id="startBtn">▶ Start Test</button>
</header>

<section class="stats">
  <div class="stat"><div class="lbl">🟢 Reachable</div><div class="val" id="stReach">—</div><div class="sub" id="stReachSub">of all sites</div></div>
  <div class="stat"><div class="lbl">⚡ Avg latency</div><div class="val" id="stAvg">—</div><div class="sub">successful connects</div></div>
  <div class="stat"><div class="lbl">🚀 Fastest site</div><div class="val" style="font-size:1.05rem" id="stFast">—</div><div class="sub" id="stFastSub">&nbsp;</div></div>
  <div class="stat"><div class="lbl">🐢 Slowest site</div><div class="val" style="font-size:1.05rem" id="stSlow">—</div><div class="sub" id="stSlowSub">&nbsp;</div></div>
</section>

<section class="filters">
  <div class="chiprow"><span class="rlbl">Category</span><span id="catChips"></span></div>
  <div class="chiprow"><span class="rlbl">Region</span><span id="regChips"></span></div>
</section>

<main id="grid"></main>

<footer>Tested via TCP connect + TLS handshake to port 443 · lower latency is better<br>
<b>NetPulse</b> runs locally — no data leaves your machine except the probe packets themselves.</footer>
</div>

<script>
const targets = [];
let results = {};
let running = false;
let activeCat = 'All', activeReg = 'All';
let nets = [], netChoice = -1;
let lastMeta = {when: null, network: 'System default'};

const $ = s => document.querySelector(s);
const flag = cc => String.fromCodePoint(...[...cc].map(c => 127397 + c.charCodeAt()));
const fmtMs = ms => ms >= 1000 ? (ms/1000).toFixed(2)+' s' : ms+' ms';
const gradeColor = ms => ms <= 120 ? 'var(--good)' : ms <= 300 ? '#a3e635' : ms <= 650 ? 'var(--mid)' : 'var(--slow)';
const gradeWord = ms => ms <= 120 ? 'Excellent' : ms <= 300 ? 'Good' : ms <= 650 ? 'Fair' : 'Slow';

function buildChips(){
  const cats = ['All', ...new Set(targets.map(t => t.cat))];
  const regs = ['All', ...new Set(targets.map(t => t.region))];
  $('#catChips').innerHTML = cats.map(c => `<button class="chip ${c==='All'?'on':''}" data-cat="${c}">${c}</button>`).join('');
  $('#regChips').innerHTML = regs.map(r => `<button class="chip ${r==='All'?'on':''}" data-reg="${r}">${r}</button>`).join('');
  $('#catChips').onclick = e => { if(!e.target.dataset.cat)return; activeCat=e.target.dataset.cat;
    [...$('#catChips').children].forEach(x=>x.classList.toggle('on',x===e.target)); applyFilters(); };
  $('#regChips').onclick = e => { if(!e.target.dataset.reg)return; activeReg=e.target.dataset.reg;
    [...$('#regChips').children].forEach(x=>x.classList.toggle('on',x===e.target)); applyFilters(); };
}
function applyFilters(){
  document.querySelectorAll('.card').forEach(c=>{
    const show = (activeCat==='All'||c.dataset.cat===activeCat)&&(activeReg==='All'||c.dataset.region===activeReg);
    c.classList.toggle('hidden',!show);
  });
}
async function loadNetworks(force){
  try{ nets = await(await fetch('/api/networks'+(force?'?refresh=1':''))).json(); }
  catch{ nets = []; }
  const sel = $('#netSel');
  sel.innerHTML = nets.map((n,i)=>`<option value="${i}">${n.online?'🟢':'⚪'} ${n.alias} — ${n.ip}</option>`).join('');
  $('#netBox').style.display = nets.length>1 ? 'flex' : 'none';
  netChoice = nets.length>1 ? 0 : -1;
  sel.value = String(Math.max(0,netChoice));
}
function summary(){
  const rs = targets.map(t=>results[t.id]).filter(Boolean);
  const ok = rs.filter(r=>r.ok), oks = ok.map(r=>r.ms);
  const avg = oks.length ? Math.round(oks.reduce((a,b)=>a+b,0)/oks.length) : null;
  const reach = rs.length ? ok.length/rs.length*100 : 0;
  const speed = avg!=null ? Math.max(0,100-avg/12) : 0;
  const score = rs.length ? Math.round(reach*.65+speed*.35*(ok.length/rs.length)) : null;
  const sorted = [...ok].sort((a,b)=>a.ms-b.ms);
  return {tested:rs.length, okCount:ok.length, avg, score,
          fast:sorted[0]||null, slow:sorted[sorted.length-1]||null};
}
function buildGrid(){
  $('#grid').innerHTML = targets.map(t=>`
    <article class="card" data-id="${t.id}" data-cat="${t.cat}" data-region="${t.region}">
      <button class="retry" title="Re-test this site">↻</button>
      <div class="c-top"><span class="flag">${flag(t.cc)}</span><span class="c-name">${t.name}</span><span class="dot"></span></div>
      <div class="c-meta"><span class="badge cat">${t.cat}</span><span class="badge reg">${t.region}</span></div>
      <div class="ms-line"><span class="ms">—</span><span class="unit"></span><span class="http"></span></div>
      <div class="bar"><i></i></div>
      <span class="state">waiting…</span>
    </article>`).join('');
  document.querySelectorAll('.retry').forEach(b=>b.onclick=e=>{
    const card=e.target.closest('.card'); retryOne(+card.dataset.id);
  });
}
function setCard(t,r){
  const card=document.querySelector(`.card[data-id="${t.id}"]`); if(!card)return;
  const dot=card.querySelector('.dot'),msEl=card.querySelector('.ms'),unit=card.querySelector('.unit'),
        bar=card.querySelector('.bar i'),state=card.querySelector('.state'),http=card.querySelector('.http');
  card.classList.remove('testing','ok','fail'); dot.className='dot';
  if(!r){ card.querySelector('.ms').textContent='—'; unit.textContent=''; bar.style.width='0';
    state.textContent='waiting…'; http.textContent=''; return; }
  if(r.ok){
    card.classList.add('ok'); dot.classList.add('ok');
    msEl.textContent=r.ms>=1000?(r.ms/1000).toFixed(2):r.ms; unit.textContent='ms · '+gradeWord(r.ms);
    msEl.style.color=gradeColor(r.ms); bar.style.width=Math.min(100,r.ms/10)+'%'; bar.style.background=gradeColor(r.ms);
    state.textContent=r.status?`HTTPS ${r.status}`:'reachable'; state.style.color=gradeColor(r.ms);
    http.textContent=r.status?('HTTP '+r.status):'';
  }else{
    card.classList.add('fail'); dot.classList.add('fail');
    msEl.textContent='✕'; msEl.style.color='var(--bad)'; unit.textContent='';
    bar.style.width='0'; state.textContent=r.error||'unreachable'; state.style.color='var(--bad)'; http.textContent='';
  }
}
function markTesting(id){
  const card=document.querySelector(`.card[data-id="${id}"]`); if(!card)return;
  card.classList.add('testing'); card.querySelector('.dot').className='dot testing';
  card.querySelector('.state').textContent='testing…';
}
async function retryOne(id){
  if(running)return;
  const t=targets.find(x=>x.id===id); if(!t)return;
  markTesting(id);
  try{ const r=await(await fetch('/api/test?id='+id+(netChoice>=0?'&net='+netChoice:''))).json(); results[id]=r; setCard(t,r); updateStats(); }
  catch{ const r={id,ok:false,error:'request failed'}; results[id]=r; setCard(t,r); updateStats(); }
}
function updateStats(){
  const s=summary();
  $('#stReach').textContent=s.tested?`${s.okCount}/${targets.length}`:'—';
  $('#stAvg').textContent=s.avg!=null?s.avg+' ms':'—';
  const name=id=>(targets.find(t=>t.id===id)||{}).name||'';
  $('#stFast').textContent=s.fast?name(s.fast.id):'—';
  $('#stFastSub').innerHTML=s.fast?fmtMs(s.fast.ms):'&nbsp;';
  $('#stSlow').textContent=(s.slow&&s.fast&&s.slow.id!==s.fast.id)?name(s.slow.id):'—';
  $('#stSlowSub').innerHTML=(s.slow&&s.fast&&s.slow.id!==s.fast.id)?fmtMs(s.slow.ms):'&nbsp;';
  const sc=s.score??0;
  $('#score').textContent=s.score!=null?s.score:'—';
  const ring=$('#ring'); ring.style.strokeDashoffset=264-264*sc/100;
  ring.style.stroke=sc>=80?'#34d399':sc>=55?'#a3e635':sc>=30?'#fbbf24':sc>0?'#fb923c':'#f87171';
  $('#reportBtn').disabled=!Object.keys(results).length;
}
function buildReportHTML(){
  const s=summary();
  const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const when=(lastMeta.when||new Date()).toLocaleString();
  const pill=r=>r.ok?'<span class="p ok">PASS</span>':'<span class="p fail">FAIL</span>';
  const groups={};
  targets.forEach(t=>{const r=results[t.id]; if(r){(groups[t.cat]=groups[t.cat]||[]).push({t,r});}});
  const sections=Object.entries(groups).map(([cat,arr])=>{
    const m=arr.filter(a=>a.r.ok).map(a=>a.r.ms);
    const avg=m.length?Math.round(m.reduce((x,y)=>x+y,0)/m.length)+' ms':'—';
    arr.sort((a,b)=>((b.r.ok?1:0)-(a.r.ok?1:0))||((a.r.ms??1e9)-(b.r.ms??1e9)));
    return `<h2>${esc(cat)}<small>${arr.filter(a=>a.r.ok).length}/${arr.length} passed · avg ${avg}</small></h2>
<table><thead><tr><th>Status</th><th>Site</th><th>Region</th><th>Latency</th><th>HTTP</th><th>Error</th></tr></thead>
<tbody>${arr.map(a=>`<tr><td>${pill(a.r)}</td><td>${esc(a.t.name)}</td><td>${esc(a.t.region)}</td><td class="m">${a.r.ok?fmtMs(a.r.ms):'—'}</td><td>${a.r.status??''}</td><td class="e">${a.r.ok?'':esc(a.r.error||'unreachable')}</td></tr>`).join('')}</tbody></table>`;
  }).join('');
  const tName=id=>esc(((targets.find(t=>t.id===id)||{}).name)||'');
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>NetPulse Test Report</title>
<style>
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f6fb;color:#1c2333;margin:0;padding:36px}
.wrap{max-width:920px;margin:0 auto}
h1{margin:0 0 4px;font-size:1.7rem}h1 b{color:#4f46e5}
.subt{color:#697086;font-size:.85rem;margin-bottom:26px}
.meta{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.mcard{flex:1;min-width:150px;background:#fff;border:1px solid #e3e7f2;border-radius:12px;padding:14px 18px}
.mcard .l{font-size:.66rem;text-transform:uppercase;letter-spacing:1.2px;color:#8a90a5;margin-bottom:5px}
.mcard .v{font-size:1.25rem;font-weight:800}
h2{font-size:1rem;margin:28px 0 10px;color:#333c56;display:flex;align-items:center;gap:10px}
h2 small{font-weight:600;font-size:.72rem;color:#8a90a5;background:#eceff7;border-radius:99px;padding:3px 10px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(20,30,70,.07);font-size:.86rem}
th{background:#eef1f9;text-align:left;padding:9px 12px;font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;color:#5b6478}
td{padding:9px 12px;border-top:1px solid #eef0f7}
.p{font-size:.64rem;font-weight:800;letter-spacing:.6px;border-radius:99px;padding:3px 9px}
.p.ok{background:#dcfce7;color:#15803d}.p.fail{background:#fee2e2;color:#b91c1c}
.m{font-variant-numeric:tabular-nums;font-weight:700}.e{color:#b91c1c;font-size:.78rem}
.rfoot{margin-top:34px;color:#98a0b5;font-size:.72rem;line-height:1.6}
@media print{body{padding:0;background:#fff}.mcard,table{box-shadow:none}}
</style></head><body><div class="wrap">
<h1>🌐 <b>NetPulse</b> — Internet Test Report</h1>
<div class="subt">Generated ${esc(when)} &nbsp;·&nbsp; Network: ${esc(lastMeta.network)} &nbsp;·&nbsp; Host: ${location.host}</div>
<div class="meta">
<div class="mcard"><div class="l">Score</div><div class="v">${s.score??'—'} / 100</div></div>
<div class="mcard"><div class="l">Reachable</div><div class="v">${s.okCount} / ${targets.length}</div></div>
<div class="mcard"><div class="l">Avg latency</div><div class="v">${s.avg!=null?s.avg+' ms':'—'}</div></div>
<div class="mcard"><div class="l">Fastest site</div><div class="v" style="font-size:1rem">${s.fast?tName(s.fast.id):'—'} <small style="color:#8a90a5;font-size:.72rem">${s.fast?fmtMs(s.fast.ms):''}</small></div></div>
<div class="mcard"><div class="l">Slowest site</div><div class="v" style="font-size:1rem">${(s.slow&&(!s.fast||s.slow.id!==s.fast.id))?tName(s.slow.id):'—'} <small style="color:#8a90a5;font-size:.72rem">${(s.slow&&(!s.fast||s.slow.id!==s.fast.id))?fmtMs(s.slow.ms):''}</small></div></div>
</div>
${sections}
<div class="rfoot">Latency = TCP connect + TLS handshake time to port 443 · PASS = reachable within timeout.<br>
Tip: open this file in any browser and press Ctrl+P to save it as PDF.</div>
</div></body></html>`;
}
function downloadReport(){
  if(!Object.keys(results).length)return;
  const blob=new Blob([buildReportHTML()],{type:'text/html'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='netpulse-report-'+new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')+'.html';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
$('#reportBtn').onclick=downloadReport;
$('#netRefresh').onclick=()=>loadNetworks(true);

async function runAll(){
  if(running)return; running=true;
  lastMeta={when:new Date(),
    network:(netChoice>=0&&nets[netChoice])?`${nets[netChoice].alias} (${nets[netChoice].ip})`:'System default'};
  const ns=$('#netSel'); if(ns)ns.disabled=true;
  results={}; targets.forEach(t=>setCard(t,null)); updateStats();
  const btn=$('#startBtn'); btn.disabled=true; btn.classList.add('running'); btn.textContent='⏳ Testing…';
  const total=targets.length; let done=0;
  try{
    const res=await fetch('/api/stream'+(netChoice>=0?'?net='+netChoice:'')); const reader=res.body.getReader();
    const dec=new TextDecoder(); let buf='';
    for(;;){
      const {done:fin,value}=await reader.read(); if(fin)break;
      buf+=dec.decode(value,{stream:true});
      let idx;
      while((idx=buf.indexOf('\n\n'))>=0){
        const frame=buf.slice(0,idx); buf=buf.slice(idx+2);
        const line=frame.split('\n').find(l=>l.startsWith('data: ')); if(!line)continue;
        const msg=JSON.parse(line.slice(6));
        if(msg.type==='result'){ done++; results[msg.result.id]=msg.result;
          setCard(targets.find(t=>t.id===msg.result.id),msg.result);
          $('#progress').style.width=(done/total*100)+'%'; updateStats(); }
      }
    }
  }catch(e){ console.error(e); }
  $('#progress').style.width='100%';
  setTimeout(()=>{$('#progress').style.width='0';},900);
  btn.disabled=false; btn.classList.remove('running'); btn.textContent='↻ Test Again';
  if(ns)ns.disabled=false;
  running=false; updateStats();
}
$('#startBtn').onclick=runAll;
(async()=>{
  const list=await(await fetch('/api/targets')).json();
  targets.push(...list);
  buildChips(); buildGrid();
  await loadNetworks();
  await runAll();
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "NetPulse/1.0"

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/targets":
            self._json(TARGETS)
        elif path == "/api/networks":
            force = "refresh=1" in self.path
            self._json(get_networks(force))
        elif path == "/api/stream":
            self.handle_stream()
        elif path == "/api/test":
            self.handle_single()
        else:
            self.send_error(404)

    @staticmethod
    def _query_param(qs, key):
        for kv in qs.split("&"):
            if kv.startswith(key + "="):
                return kv[len(key) + 1:]
        return None

    def handle_single(self):
        qs = self.path.split("?", 1)[1] if "?" in self.path else ""
        tid = None
        try:
            tid = int(self._query_param(qs, "id"))
        except (TypeError, ValueError):
            pass
        try:
            net = int(self._query_param(qs, "net"))
        except (TypeError, ValueError):
            net = -1
        t = BY_ID.get(tid)
        if t is None:
            self._json({"error": "unknown id"}, 400)
            return
        result = run_test(t, resolve_src_ip(net))
        self._json(result)

    def handle_stream(self):
        qs = self.path.split("?", 1)[1] if "?" in self.path else ""
        try:
            net = int(self._query_param(qs, "net"))
        except (TypeError, ValueError):
            net = -1
        src_ip = resolve_src_ip(net)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def emit(payload):
            self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
            self.wfile.flush()

        try:
            with ThreadPoolExecutor(max_workers=16) as pool:
                futures = {pool.submit(run_test, t, src_ip): t for t in TARGETS}
                for fut in as_completed(futures):
                    result = fut.result()
                    emit({"type": "result", "result": result})
            emit({"type": "done"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


def main():
    port = DEFAULT_PORT
    args = sys.argv[1:]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    open_browser = "--no-browser" not in args

    server = ThreadingHTTPServer((HOST, port), Handler)
    url = f"http://{HOST}:{port}"
    print(f"NetPulse running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
