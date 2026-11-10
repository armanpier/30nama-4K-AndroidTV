# Gemini Desktop Screenshare for Windows

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D6?logo=windows)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/UI-PyQt6%20(Material%20Dark)-41CD52?logo=qt)](https://www.qt.io/)
[![Protocol](https://img.shields.io/badge/Protocol-Gemini%20Multimodal%20Live%20WS-8E75C2)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

A high-performance, native Windows desktop application that brings the **Google Gemini Live screen sharing experience**—previously exclusive to Android mobile devices—to Microsoft Windows 10 and 11. 

Authenticate seamlessly with your **Google Account** (no raw API keys required), stream your desktop display or individual application windows in real time with bidirectional voice conversation, or capture instant snapshots with targeted queries using global system hotkeys.

---

## Table of Contents
1. [Key Features](#-key-features)
2. [Architecture Overview](#-architecture-overview)
3. [System Requirements & Prerequisites](#-system-requirements--prerequisites)
4. [Quick Start Guide](#-quick-start-guide)
5. [Google Cloud OAuth 2.0 Setup Guide](#-google-cloud-oauth-20-setup-guide)
6. [User Interface & Controls Guide](#-user-interface--controls-guide)
7. [Global System Hotkeys Cheat Sheet](#-global-system-hotkeys-cheat-sheet)
8. [Audio Pipeline & Barge-In Interruption](#-audio-pipeline--barge-in-interruption)
9. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## ✨ Key Features

- **Dual-Mode Desktop Interaction**:
  - **Continuous Live Streaming**: Streams 1.0 FPS downscaled JPEG desktop frames (~1024px) paired with 16kHz 16-bit linear PCM microphone audio over a bidirectional WebSocket to the Gemini Multimodal Live API. Plays back real-time 24kHz model speech with sub-millisecond barge-in interruption.
  - **On-Demand Capture & Query**: Instant snapshot of the full desktop or a specific application window triggered via UI button or global hotkey (`Alt+S`), paired with custom or preset queries (`Explain Screen`, `Summarize`, `Detect Errors`, `Translate`).
- **Google Account Authentication (Zero API Keys)**:
  - Standard RFC 8252 OAuth 2.0 for Native Apps with RFC 7636 PKCE S256.
  - Launches your default desktop browser (Chrome, Edge, Firefox) with an ephemeral loopback redirect (`http://127.0.0.1:<port>`).
  - Refresh tokens encrypted and stored securely in the **Windows Credential Manager** (`WinVaultKeyring`) with automatic Windows DPAPI fallback.
  - Automatic, proactive token refresh (5 minutes before expiration).
- **Flexible Capture Targets**:
  - **Multi-Monitor Full Desktop**: Captures the entire virtual screen or primary monitor using ultra-fast `mss` (~20ms).
  - **Window-Specific Capture**: Hardware-accelerated Win32 window capture via `PrintWindow(PW_RENDERFULLCONTENT)` with `DWMWA_EXTENDED_FRAME_BOUNDS` and minimized window UX protection.
- **Modern Google Material 3 Dark UI**:
  - Master-detail card deck built with PyQt6.
  - Live 1.0 FPS target thumbnail preview.
  - Rich conversation transcript with smart auto-scroll, markdown rendering, and barge-in notices.
  - Microphone mute toggle that injects silence PCM packets into the live audio stream.
- **Global Win32 System Hotkeys**:
  - `Alt+S`: Trigger on-demand snapshot analysis from anywhere in Windows.
  - `Alt+L`: Toggle continuous live streaming without bringing the application to focus.

---

## 🏛 Architecture Overview

```
+───────────────────────────────────────────────────────────────────────────+
|                           PyQt6 Modern Desktop GUI                        |
|   • Google Account Status Card    • Target Window / Monitor Picker        |
|   • Live / On-Demand Mode Toggle  • Live Preview Thumbnail (340x192)      |
|   • Mic Mute Toggle               • Rich Conversation Transcript          |
+───────────────────────────────────────────────────────────────────────────+
       │                                                      ▲
       │ (Thread-Safe Qt Signals)                             │ (Qt Signals)
       ▼                                                      │
+───────────────────────────────────────────────────────────────────────────+
|                     AsyncWorker (Dedicated Asyncio QThread)               |
|                                                                           |
|   +──────────────────────────+       +────────────────────────────────+   |
|   | Screen Capture Engine    |       | Audio Pipeline                 |   |
|   | • mss (Full Desktop)     |       | • 16kHz PCM Mic Capture        |   |
|   | • PrintWindow (Win32 HWND)|      | • 24kHz PCM Model Playback     |   |
|   | • 1024px Scaler & JPEG Q70|      | • Barge-in Queue Purge (<0.1ms)|   |
|   +──────────────────────────+       +────────────────────────────────+   |
|                │                                     │                    |
|                ▼                                     ▼                    |
|   +───────────────────────────────────────────────────────────────────+   |
|   | Gemini Multimodal Live Client (WebSocket / TLS 1.3)               |   |
|   | • Bearer Token Auth (websockets 14+ additional_headers)           |   |
|   | • Realtime multiplexed mediaChunks (1 FPS video + 16kHz audio)    |   |
|   | • Server-side VAD & Interruption handling                         |   |
|   +───────────────────────────────────────────────────────────────────+   |
|                                                                           |
|   +───────────────────────────────────────────────────────────────────+   |
|   | On-Demand REST Client (aiohttp / generateContent)                 |   |
|   | • High-res JPEG snapshot + user prompt payload                    |   |
|   | • Markdown-formatted candidate extraction                         |   |
|   +───────────────────────────────────────────────────────────────────+   |
+───────────────────────────────────────────────────────────────────────────+
```

---

## 💻 System Requirements & Prerequisites

- **Operating System**: Microsoft Windows 10 (64-bit) or Windows 11 (64-bit).
- **Python**: Version **3.10**, **3.11**, or **3.12** (64-bit).
- **Audio Hardware**: Any functional microphone (input) and speakers/headphones (output).
- **Google Cloud Project**: A standard Google Cloud Project with the **Generative Language API** or **Vertex AI API** enabled.

---

## 🚀 Quick Start Guide

### 1. Clone & Navigate to Repository
```powershell
git clone https://github.com/your-org/gemini_desktop_screenshare.git
cd gemini_desktop_screenshare
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r gemini_desktop_screenshare/requirements.txt
```

### 4. Configure Google Cloud OAuth Credentials
Set your Google Cloud OAuth Client credentials via environment variables (recommended):
```powershell
$env:GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "GOCSPX-YOUR_CLIENT_SECRET"
```
*(Alternatively, configure them in `~/.gemini_desktop_screenshare/config.json` as described below).*

### 5. Launch the Application
Run via module syntax:
```powershell
python -m gemini_desktop_screenshare.app
```
Or directly via script:
```powershell
python gemini_desktop_screenshare/app.py
```

---

## 🔑 Google Cloud OAuth 2.0 Setup Guide

To enable Google Account sign-in without manual API keys, configure a standard OAuth 2.0 Desktop Client in the Google Cloud Console:

### Step 1: Create or Select a Google Cloud Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top bar and select **New Project**.
3. Name your project (e.g., `Gemini-Desktop-Screenshare`) and click **Create**.

### Step 2: Enable the Required APIs
1. Go to **APIs & Services** > **Library**.
2. Search for **Generative Language API** (or **Vertex AI API**) and click **Enable**.

### Step 3: Configure the OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** user type and click **Create**.
3. Fill in the required fields:
   - **App name**: `Gemini Desktop Screenshare`
   - **User support email**: Your email address.
   - **Developer contact information**: Your email address.
4. Click **Save and Continue**.
5. Under **Scopes**, click **Add or Remove Scopes** and select:
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/cloud-platform`
   - `https://www.googleapis.com/auth/generative-language`
6. Click **Save and Continue**.
7. Under **Test Users**, add the Google email address(es) you will use to sign in. Click **Save and Continue**.

### Step 4: Create OAuth 2.0 Desktop Client ID
1. Go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Under **Application type**, select **Desktop app**.
4. Name the client (e.g., `Gemini Desktop Client`).
5. Click **Create**.
6. Copy the generated **Client ID** and **Client Secret**.

*(Note: Per RFC 8252 §8.3, Google's "Desktop app" client type automatically supports any dynamic ephemeral loopback port on `http://127.0.0.1`. You do NOT need to register individual port numbers).*

### Step 5: Configure Credentials in the Application
You can supply credentials using either of the following methods:

**Method A: Environment Variables (Recommended for PowerShell / CMD)**:
```powershell
$env:GOOGLE_CLIENT_ID = "1028741369348-sample.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "GOCSPX-sampleSecret"
```

**Method B: JSON Configuration File**:
Create or edit `~/.gemini_desktop_screenshare/config.json`:
```json
{
  "client_id": "1028741369348-sample.apps.googleusercontent.com",
  "client_secret": "GOCSPX-sampleSecret",
  "voice_name": "Aoede",
  "video_fps": 1.0,
  "jpeg_quality": 70
}
```

---

## 🖥 User Interface & Controls Guide

The application features a modern dark card-deck layout designed for effortless desktop multi-tasking:

### 1. Google Account Card
- **Sign In with Google**: Opens your default system browser to complete the RFC 8252 PKCE sign-in flow. Upon consent, the browser redirects to the local loopback server (`127.0.0.1:<port>`), retrieves tokens, and automatically closes the browser tab.
- **User Profile**: Displays your authenticated Google name, email address, and profile avatar.
- **↻ Refresh Token**: Proactively refreshes your OAuth access token on demand.
- **Sign Out**: Revokes the refresh token with Google's servers, purges stored credentials from Windows Credential Manager, and returns the app to unauthenticated state.

### 2. Interaction Mode Card
- **Continuous Live Streaming**: Activates bidirectional real-time video/audio streaming with Gemini. The model continuously observes your screen and speaks answers over your audio output device.
- **On-Demand Screen Capture**: Switches to snapshot mode. Use this when you want to ask discrete questions about specific screens or code snippets.

### 3. Capture Target Card
- **Full Desktop (All Displays)**: Captures your entire desktop canvas (including multi-monitor setups).
- **Application Window**: Dynamically lists all active, top-level Windows applications with their HWND, title, and dimensions.
  - **↻ Window Refresh**: Re-enumerates active windows without restarting the stream.
  - **Minimized Window UX Protection**: If a selected window is minimized, the app displays a clean `[Window Minimized]` placeholder instead of stealing focus or popping up over your work.

### 4. Session Controls Card
- **Start / Stop Live Streaming**: Primary action button. Changes to red **Stop Live Streaming** while active.
- **🎤 Microphone Mute Toggle**: Click to toggle between **Active (Unmuted)** and **MUTED**. When muted, the application injects silence PCM frames (`b'\x00' * 3200`) into the live stream to prevent ambient noise transmission without interrupting the WebSocket protocol.

### 5. Live Target Preview Card
- Displays a real-time 340x192 downscaled preview thumbnail of what Gemini currently sees, updating smoothly.

### 6. Conversation & Live Transcript Deck
- **Transcript View**: Live streaming token display showing real-time text responses from Gemini alongside user speech turns.
- **Barge-In Notice**: Renders a highlighted `— ⚡ Interrupted by user speech —` divider whenever you interrupt the model.
- **Smart Auto-Scroll**: Automatically scrolls to the bottom during active speech. If you scroll up to inspect previous turns, auto-scroll pauses and a floating **↓ Jump to Latest** button appears.
- **Copy & Clear**: One-click copying of the complete markdown transcript to the Windows clipboard.

### 7. On-Demand Prompt Dock (On-Demand Mode)
- **Preset Chips**: One-click quick analysis chips:
  - `🔍 Explain Screen`: High-level explanation of visible UI or documents.
  - `📝 Summarize`: Summarizes key textual data in the active window.
  - `🐛 Detect Errors`: Analyzes code, terminals, or dialogs for error traces.
  - `🌐 Translate`: Translates foreign text on screen to English.
- **Custom Query Input**: Type any question and press `Enter` or click **Send Query**.

---

## ⌨ Global System Hotkeys Cheat Sheet

Global hotkeys operate from any application or game in Windows without needing focus on the Gemini Desktop window:

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`Alt + S`** | **On-Demand Snapshot & Query** | Snaps the active display or chosen window, submits the query in the dock, and displays the response. |
| **`Alt + L`** | **Toggle Continuous Live Stream** | Starts continuous streaming if idle; stops streaming if active. |

*Conflict Resilience*: If another software (e.g. GeForce Experience, Snagit) already occupies `Alt+S` or `Alt+L`, the application logs a non-blocking warning (Win32 Error 1409) and allows full operation via UI buttons.

---

## 🎙 Audio Pipeline & Barge-In Interruption

- **Microphone Capture**: 16,000 Hz, 16-bit Mono linear PCM buffered into 100ms chunks (3,200 bytes).
- **Model Speech Playback**: 24,000 Hz, 16-bit Mono linear PCM rendered via a callback-driven non-blocking WASAPI/MME audio stream (`sounddevice.RawOutputStream`).
- **Instant Barge-In Interruption (<0.1ms)**:
  - When you speak while Gemini is talking, Gemini's server-side Voice Activity Detection (VAD) detects speech phonemes and transmits an `{ serverContent: { interrupted: true } }` message.
  - The client instantly drains the playback queue in **0.05ms** without invoking driver-stopping calls (`stream.stop()`), eliminating the 250ms driver stall typical of standard audio libraries.

---

## ❓ Troubleshooting & FAQs

### Q1: PyAudio / sounddevice initialization fails (`PortAudio error` or `No Default Input Device`)
- **Cause**: Windows microphone permissions are disabled, or no default recording device is selected.
- **Resolution**:
  1. Open Windows **Settings** > **Privacy & Security** > **Microphone**.
  2. Ensure **Microphone access** is turned **On** and **Let desktop apps access your microphone** is enabled.
  3. Verify a default recording device is enabled in the Windows Sound Control Panel (`mmsys.cpl`).

### Q2: Global hotkey registration warning: "Hotkey already registered by another application (Error 1409)"
- **Cause**: Another tool (such as Nvidia GeForce Overlay, OBS, or AMD Adrenalin) has registered `Alt+S` or `Alt+L`.
- **Resolution**: You can continue using all features by clicking the UI buttons. To free the hotkeys, rebind or disable conflicting shortcuts in the respective third-party application.

### Q3: Black screen captured for certain windows (e.g. Netflix, Chrome, Task Manager)
- **Cause**: Hardware-accelerated overlays or Windows Elevated Protected Windows (UAC/System).
- **Resolution**:
  1. The application automatically detects pure black frames from `PrintWindow` and falls back to foreground `mss` desktop cropping.
  2. For browser windows, disable "Use hardware acceleration when available" in Chrome/Edge settings if DRM content prevents capture.
  3. For elevated applications (e.g. Task Manager, Process Hacker), run `gemini_desktop_screenshare` as Administrator.

### Q4: Google Sign-In gives `Error 400: invalid_request` or `redirect_uri_mismatch`
- **Cause**: OAuth Client ID was created as "Web application" instead of "Desktop app".
- **Resolution**: In Google Cloud Console, delete the client ID and create a new OAuth Client ID choosing **Application type: Desktop app**. Desktop client IDs dynamically permit `http://127.0.0.1:<port>`.

### Q5: "Token refresh failed" error message appears
- **Cause**: The refresh token was revoked, expired (after 6 months of inactivity), or the test user was removed from the Google Cloud Console consent screen.
- **Resolution**: Click **Sign Out** in the application, then click **Sign In with Google** to establish a fresh session.
