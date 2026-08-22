# 🌐 NetPulse — Global Internet Tester

A beautiful, zero-dependency internet connectivity tester that probes **58 websites across 7 world regions and 9 categories** — then streams live results to a sleek glassmorphism dashboard in your browser.

![Python](https://img.shields.io/badge/python-3.8%2B-3776ab?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Dependencies](https://img.shields.io/badge/dependencies-0-success)

## ✨ Features

- 🌍 **Global coverage** — tests sites across North & South America, Europe, Asia, Middle East, Africa, and Oceania
- 🗂️ **9 categories** — Search, Social, Streaming, AI, Cloud & Dev, News, Shopping, Messaging
- ⚡ **Real latency measurement** — TCP connect + TLS handshake timing to port `443`, plus HTTP status detection
- 📡 **Network adapter selector** — multiple networks? Pick exactly which adapter (Ethernet, Wi-Fi, VPN…) to test through
- 📊 **Live streaming dashboard** — results appear one-by-one as they complete, with a score gauge, stat cards, and per-site latency bars
- 🔍 **Filters** — drill down by category or region; re-test any single site with the ↻ button
- ⬇️ **Downloadable report** — export a polished, self-contained HTML report (print it to PDF with Ctrl+P)
- 🪶 **Zero dependencies** — pure Python standard library. No pip install. One file.

## 🚀 Quick Start

```bash
python internet_tester.py
```

That's it. Your browser opens at `http://127.0.0.1:8765` and a test starts automatically.

### Command-line options

| Flag | Description |
|------|-------------|
| `--port <n>` | Run on a custom port (default: `8765`) |
| `--no-browser` | Don't auto-open the browser |

## 🖥️ Dashboard Preview

| | |
|---|---|
| Score gauge + live stats | Category / region filter chips |
| Per-site cards with latency bars & HTTP status | Network adapter picker + report download |

> 📸 *Run it and see for yourself — dark glass UI with animated gradient blobs.*

## 📖 How It Works

1. **Probing** — each target is tested by opening a raw TCP connection to port `443` (connect time = latency), then attempting a TLS handshake + `HEAD` request to capture the HTTP status code.
2. **Concurrency** — all 58 targets are tested simultaneously via a thread pool (16 workers), so a full sweep takes just a few seconds.
3. **Streaming** — results are pushed to the dashboard as an event stream (`/api/stream`) the moment each test finishes.
4. **Scoring** — `score = reachability × 65% + speed × 35%`, where reachability is the % of sites that responded and speed is derived from average latency.

### Latency grades

| Latency | Grade |
|---------|-------|
| ≤ 120 ms | 🟢 Excellent |
| ≤ 300 ms | 🟢 Good |
| ≤ 650 ms | 🟡 Fair |
| > 650 ms | 🟠 Slow |

### API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard UI |
| `GET /api/targets` | All monitored sites as JSON |
| `GET /api/networks[?refresh=1]` | List network adapters (alias, IP, gateway) |
| `GET /api/stream[?net=N]` | SSE-style live test stream |
| `GET /api/test?id=ID&net=N` | Re-test a single site |

## 📡 Network Selection

If your machine has multiple network adapters (e.g., Ethernet + Wi-Fi + VPN), a picker appears in the header. Tests bind their source address to the chosen adapter's IP, so you can compare real-world performance per connection. The list is detected natively on Windows and refreshed on demand.

## 📋 Requirements

- Python **3.8+**
- Windows (for adapter enumeration; everything else is cross-platform)

## 🤝 Contributing

Contributions are welcome! Some ideas:

- [ ] More global targets (add rows to `T` in `internet_tester.py`)
- [ ] Ping (ICMP) mode alongside TCP
- [ ] Historical charts of past runs
- [ ] Cross-platform adapter detection (macOS/Linux)

1. Fork the repo
2. Create your branch (`git checkout -b feature/awesome`)
3. Commit changes (`git commit -m 'Add awesome'`)
4. Push (`git push origin feature/awesome`) and open a PR

## 📄 License

Released under the [MIT License](LICENSE) — free to use, modify, and share.

---

<p align="center">Made with 🧡 and pure Python</p>
