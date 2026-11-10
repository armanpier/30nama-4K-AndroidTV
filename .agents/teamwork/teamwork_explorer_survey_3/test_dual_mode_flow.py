import asyncio
import json
import base64
import time
import io
import ctypes
from PIL import Image, ImageGrab
import mss
from mock_gemini_server import MockGeminiLiveServer

def safe_screen_capture(sct_instance=None):
    """Robust screen capture with retry and fallback."""
    for attempt in range(2):
        try:
            if sct_instance:
                mon = sct_instance.monitors[1]
                sct_img = sct_instance.grab(mon)
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            else:
                with mss.MSS() as sct:
                    mon = sct.monitors[1]
                    sct_img = sct.grab(mon)
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            time.sleep(0.05)
    # Fallback to PIL ImageGrab
    return ImageGrab.grab()

import websockets

async def run_dual_mode_verification():
    print("=== Starting Dual-Mode Live Verification against Mock Gemini Server ===")
    port = 8991
    server = MockGeminiLiveServer(host="127.0.0.1", port=port)
    await server.start()
    print(f"Mock server running on ws://127.0.0.1:{port}")

    uri = f"ws://127.0.0.1:{port}"
    async with websockets.connect(uri) as ws:
        # Step 1: Send Setup
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": "Puck"}
                        }
                    }
                }
            }
        }
        await ws.send(json.dumps(setup_msg))
        resp = await ws.recv()
        setup_ack = json.loads(resp)
        assert "setupComplete" in setup_ack, f"Unexpected ack: {setup_ack}"
        print("[Pass] Session setup acknowledged by server.")

        # Step 2: Mode 1 - Stream 4 frames (at ~1 FPS) + audio chunks
        received_model_turns = 0
        with mss.MSS() as sct:
            for frame_idx in range(4):
                # Capture frame safely
                img = safe_screen_capture(sct)
                img_resized = img.resize((1024, 768), Image.Resampling.BILINEAR)
                buf = io.BytesIO()
                img_resized.save(buf, format="JPEG", quality=70)
                jpg_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

                # Dummy 16kHz audio chunk (100ms: 1600 samples * 2 bytes = 3200 bytes)
                audio_b64 = base64.b64encode(b"\x00\x00" * 1600).decode("ascii")

                realtime_msg = {
                    "realtime_input": {
                        "media_chunks": [
                            {"mime_type": "audio/pcm;rate=16000", "data": audio_b64},
                            {"mime_type": "image/jpeg", "data": jpg_b64}
                        ]
                    }
                }
                await ws.send(json.dumps(realtime_msg))
                print(f"[Mode 1] Sent frame {frame_idx + 1} ({len(buf.getvalue())/1024:.1f} KB) + audio chunk")

                # Check if server responded with model turn
                try:
                    server_msg_str = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    server_msg = json.loads(server_msg_str)
                    if "serverContent" in server_msg:
                        parts = server_msg["serverContent"]["modelTurn"]["parts"]
                        print(f"  <- Received model turn with {len(parts)} parts: {[p.get('text', 'audio_data') for p in parts]}")
                        received_model_turns += 1
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(0.3) # Simulation delay

        # Step 3: Mode 2 - On-Demand capture snapshot with query
        print("\n[Mode 2] Triggering On-Demand Screen Analysis...")
        img = safe_screen_capture()
        img_resized = img.resize((1024, 768), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img_resized.save(buf, format="JPEG", quality=80)
        snapshot_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        on_demand_msg = {
            "client_content": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Explain what is shown on this screen right now."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": snapshot_b64}}
                        ]
                    }
                ],
                "turn_complete": True
            }
        }
        await ws.send(json.dumps(on_demand_msg))
        resp_str = await ws.recv()
        resp_data = json.loads(resp_str)
        print(f"[Mode 2] Received response: {resp_data['serverContent']['modelTurn']['parts'][0]['text']}")

    await server.stop()
    print("\n=== Verification Successful! All Dual-Mode flows verified programmatically. ===")

if __name__ == '__main__':
    # Ensure thread desktop access
    import ctypes
    user32 = ctypes.windll.user32
    h = user32.OpenInputDesktop(0, False, 0x01FF)
    if h:
        user32.SetThreadDesktop(h)
    asyncio.run(run_dual_mode_verification())
