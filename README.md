# 🎬 30nama 4K — Android TV & Kodi Edition
### ۳۰نما — نسخه اختصاصی اندروید تی‌وی و پخش مستقیم 4K

[![Platform](https://img.shields.io/badge/Platform-Android%20TV%20%7C%20Google%20TV%20%7C%20Kodi-1793d1?logo=android)](https://github.com/armanpier/30nama-4K-AndroidTV/releases)
[![Resolution](https://img.shields.io/badge/Playback-4K%20UHD%20%7C%201080p%20Bluray-gold)](https://github.com/armanpier/30nama-4K-AndroidTV/releases)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20ARMv7%20%7C%20x86-brightgreen)](https://github.com/armanpier/30nama-4K-AndroidTV/releases)
[![Language](https://img.shields.io/badge/Typography-Persian%20%28Farsi%29-blue)](#-راهنمای-فارسی)
[![License](https://img.shields.io/badge/License-GPL%20v3.0-lightgrey)](LICENSE)

A high-performance, standalone Android TV application and all-in-one Kodi video addon for seamless **30nama** streaming in **4K Ultra HD** and **1080p Bluray** with zero configuration required.

Designed specifically for the 10-foot living room experience: fully navigable via TV remote (D-Pad), with native Persian font rendering, automatic subtitle synchronization, and anti-censorship proxy integration.

---

## 📥 Download Standalone APKs (First Release v1.0.0)

Pre-built, signed, and aligned single-file APK packages ready to install on your Android TV:

| Architecture | Recommended Device | Package | Direct Download |
| :--- | :--- | :--- | :--- |
| **ARM64 (v8a)** *(Recommended)* | Sony Bravia, Chromecast with Google TV (4K), Nvidia Shield, Xiaomi Box S (2nd Gen), Onn 4K Pro, TCL | `30nama-4K-AndroidTV-arm64-v8a.apk` | [Download ARM64](https://github.com/armanpier/30nama-4K-AndroidTV/releases/download/v1.0.0/30nama-4K-AndroidTV-arm64-v8a.apk) |
| **ARMv7 (32-bit)** | Older Xiaomi Mi Box 3/4, Fire TV Stick 4K (32-bit OS), Chromecast (HD) | `30nama-4K-AndroidTV-armeabi-v7a.apk` | [Download ARMv7](https://github.com/armanpier/30nama-4K-AndroidTV/releases/download/v1.0.0/30nama-4K-AndroidTV-armeabi-v7a.apk) |
| **x86 / x86_64** | Android TV Emulators, PC Android-x86, Intel TV boxes | `30nama-4K-AndroidTV-x86.apk` | [Download x86](https://github.com/armanpier/30nama-4K-AndroidTV/releases/download/v1.0.0/30nama-4K-AndroidTV-x86.apk) |
| **Kodi Addon Zip** | Existing Kodi 20/21 installs on Windows, macOS, Linux, Android, CoreELEC | `plugin.video.30nama.zip` | [Download Addon Zip](https://github.com/armanpier/30nama-4K-AndroidTV/releases/download/v1.0.0/plugin.video.30nama.zip) |

---

## ✨ Features

- **🚀 Instant Auto-Launch**: Boots directly into the 30nama catalog on app launch—no navigating through menus or addons.
- **💎 4K Ultra HD & 1080p Direct Playback**: High-bitrate streaming with hardware decoding and preconfigured 256 MB RAM cache.
- **🇮🇷 Persian Typography (Arial Preconfigured)**: Custom font subsystem ensures Persian characters never render as boxes or question marks.
- **💬 Persian & English Subtitles Engine**: Automatically downloads, extracts ZIP archives, converts legacy CP1256 encoding to clean UTF-8, and attaches subtitles instantly.
- **📺 10-Foot Leanback UI**: Custom Android TV banner, poster grid views, and full D-Pad remote control support.
- **🔐 QR Code / TV Login**: Log in effortlessly from your mobile phone or browser without typing credentials on your TV.
- **🛡️ Built-in Proxy Support**: Pre-configured HTTP proxy routing for bypassing network restrictions.
- **📦 Zero External Dependencies**: All Python networking libraries (`requests`, `urllib3`, etc.) are bundled directly inside the APK.

---

## 🛠️ How to Sideload onto Android TV

### Method 1: Via ADB (Over Wi-Fi)
```bash
# 1. Enable Developer Options & Network Debugging on your Android TV
# 2. Connect from your PC:
adb connect 192.168.1.XXX:5555

# 3. Sideload the ARM64 APK:
adb install -r 30nama-4K-AndroidTV-arm64-v8a.apk
```

### Method 2: Via USB Drive
1. Download `30nama-4K-AndroidTV-arm64-v8a.apk` to a USB flash drive.
2. Insert the flash drive into your TV box.
3. Open any file manager on Android TV (*X-plore*, *FX*, or *File Commander*) and click the APK to install.

### Method 3: "Send Files to TV" App
1. Install **Send Files to TV** on your smartphone and your Android TV.
2. Transfer the APK file wirelessly to your TV and launch it with a package installer.

---

## 🔌 Installing as a Kodi Addon (Manual)

If you already run Kodi (v20 Nexus or v21 Omega) on any operating system:

1. Download [`plugin.video.30nama.zip`](https://github.com/armanpier/30nama-4K-AndroidTV/releases/download/v1.0.0/plugin.video.30nama.zip).
2. Open Kodi → **Settings** → **System** → **Add-ons** → Enable **Unknown Sources**.
3. Go to **Add-ons** → **Install from zip file** → Select `plugin.video.30nama.zip`.
4. Open **Settings** → **Interface** → **Skin** → **Fonts** → Set to **Arial based** (essential for Persian characters).

---

## 🇮🇷 راهنمای فارسی

اپلیکیشن مستقل و افزونه اختصاصی **۳۰نما برای تلویزیون‌های هوشمند اندروید (Android TV و Google TV)**.

### ویژگی‌های کلیدی:
* **پخش مستقیم با کیفیت 4K و 1080p بلوری**: پخش آنلاین فیلم‌ها و سریال‌ها با بالاترین بیت‌ریت و بافر بهینه‌سازی شده.
* **فونت فارسی زیبا و اصلاح‌شده**: سیستم فونت به صورت خودکار روی Arial تنظیم شده تا حروف فارسی بدون هیچ‌گونه به‌هم‌ریختگی یا نمایش به شکل مربع نمایش داده شوند.
* **پشتیبانی خودکار از زیرنویس فارسی**: دانلود خودکار زیرنویس، تبدیل انکودینگ‌های قدیمی (CP1256 و ویندوز عربی) به UTF-8 استاندارد، و الحاق خودکار به فیلم.
* **ورود آسان با کد تلویزیون (QR Code)**: بدون نیاز به تایپ رمز عبور طولانی با کنترل تلویزیون، تنها با اسکن بارکد یا وارد کردن کد ۶ رقمی در گوشی وارد حساب خود شوید.
* **نصب تک‌فایلی (Single APK)**: نیازی به نصب جداگانه کوودی یا افزونه نیست؛ این بسته به شکل یک برنامه کامل با نام و آیکون اختصاصی **30TV** روی تلویزیون شما نصب می‌شود.

---

## 🏗️ Building from Source

To build your own standalone APK variants from source:

```bash
# Prerequisites: Python 3.10+, Android SDK build-tools (zipalign & apksigner)

# 1. Clone repository
git clone https://github.com/armanpier/30nama-4K-AndroidTV.git
cd 30nama-4K-AndroidTV

# 2. Download base packages and build all architectures
python download_and_build_arm.py
```

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.
