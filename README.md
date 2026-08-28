# 📻 My Online Radio (Live Broadcast + Recorded AutoDJ)

A 24/7 cloud internet radio server that supports **both live microphone broadcasting** and **recorded audio playlist fallback**, compatible with all internet radios (including **Choyong LC90**, web browsers, VLC, and mobile devices).

---

## ✨ Features

* **🔴 Live Broadcasting**: Stream live from your smartphone (using *BroadcastMySelf* / *Larix Broadcaster*) or from your PC (using *BUTT* / *OBS* / *Mixxx*).
* **📻 AutoDJ Playlist**: Automatically loops and shuffles recorded MP3 files from the `audio/` folder when no one is broadcasting live.
* **⚡ Seamless Switching**: Automatically switches to Live when you start speaking, and smoothly fades back to recorded music when you stop.
* **🌐 Web Player**: Beautiful HTML5 responsive web player with real-time "LIVE" vs "RECORDED" badges.
* **📻 Hardware Radio Support**: Permanent `/radio.mp3` stream for Choyong LC90.

---

## 🎵 How to Add Recorded Songs / Programs

1. Add your `.mp3` files into the `audio/` folder in this GitHub repository.
2. Commit and push to GitHub — Render will automatically include them in your station playlist!

---

## 📻 How to Listen on Choyong LC90:

* **Station Name:** `My Online Radio`
* **Broadcast URL:** `https://onlineradio.onrender.com/radio.mp3`
* **Select Codec:** **`MP3`**
* **Station Bitrate:** **`128Kb`**
