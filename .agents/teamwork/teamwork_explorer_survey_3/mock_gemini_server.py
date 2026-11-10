import asyncio
import json
import base64
import websockets

class MockGeminiLiveServer:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.server = None
        self.received_audio_chunks = 0
        self.received_image_chunks = 0
        self.setup_received = False
        self.stop_event = asyncio.Event()

    async def handler(self, websocket):
        try:
            async for message in websocket:
                data = json.loads(message)
                
                # 1. Setup message
                if "setup" in data:
                    self.setup_received = True
                    # Respond with setupComplete
                    await websocket.send(json.dumps({"setupComplete": {}}))
                    continue

                # 2. Realtime input chunks
                if "realtime_input" in data:
                    chunks = data["realtime_input"].get("media_chunks", [])
                    for chunk in chunks:
                        mime = chunk.get("mime_type", "")
                        if "audio/pcm" in mime:
                            self.received_audio_chunks += 1
                        elif "image/jpeg" in mime:
                            self.received_image_chunks += 1
                    
                    # Respond occasionally with audio/pcm response
                    if self.received_image_chunks > 0 and self.received_image_chunks % 2 == 0:
                        # Dummy 24kHz PCM chunk (100ms)
                        dummy_pcm = b"\x00\x00" * 2400
                        b64_audio = base64.b64encode(dummy_pcm).decode("ascii")
                        response = {
                            "serverContent": {
                                "modelTurn": {
                                    "parts": [
                                        {"text": f"Received frame {self.received_image_chunks}"},
                                        {"mimeType": "audio/pcm;rate=24000", "data": b64_audio}
                                    ]
                                },
                                "turnComplete": True
                            }
                        }
                        await websocket.send(json.dumps(response))

                # 3. Client turn / On-demand text prompt
                if "client_content" in data:
                    response = {
                        "serverContent": {
                            "modelTurn": {
                                "parts": [
                                    {"text": "On-demand capture received and analyzed."}
                                ]
                            },
                            "turnComplete": True
                        }
                    }
                    await websocket.send(json.dumps(response))

        except websockets.exceptions.ConnectionClosed:
            pass

    async def start(self):
        self.server = await websockets.serve(self.handler, self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
