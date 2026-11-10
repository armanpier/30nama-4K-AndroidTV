import asyncio
from aiohttp import web
import json
import base64

class MockGeminiRESTServer:
    def __init__(self, host="127.0.0.1", port=8992):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.router.add_post("/v1beta/models/{model}:generateContent", self.handle_generate_content)
        self.runner = None
        self.last_received_prompt = None
        self.last_received_image_bytes = None

    async def handle_generate_content(self, request):
        model = request.match_info.get("model")
        auth_header = request.headers.get("Authorization", "")
        body = await request.json()

        # Extract prompt and image
        contents = body.get("contents", [])
        prompt_text = ""
        image_data = None
        for c in contents:
            for part in c.get("parts", []):
                if "text" in part:
                    prompt_text += part["text"]
                elif "inline_data" in part:
                    image_data = base64.b64decode(part["inline_data"]["data"])

        self.last_received_prompt = prompt_text
        self.last_received_image_bytes = image_data

        response_body = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": f"Mock Gemini analysis for model {model}: I see an image of {len(image_data) if image_data else 0} bytes. The user asked: '{prompt_text}'."
                            }
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        return web.json_response(response_body)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

async def test_rest_mock():
    server = MockGeminiRESTServer()
    await server.start()
    print("REST Mock Server running...")

    import aiohttp
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:{server.port}/v1beta/models/gemini-2.0-flash:generateContent"
        dummy_img = base64.b64encode(b"\xFF\xD8\xFF\xE0\x00\x10JFIF").decode("ascii")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Analyze this screenshot"},
                        {"inline_data": {"mime_type": "image/jpeg", "data": dummy_img}}
                    ]
                }
            ]
        }
        headers = {"Authorization": "Bearer mock-token-12345"}
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            print("Response:", data["candidates"][0]["content"]["parts"][0]["text"])

    await server.stop()
    print("REST Mock test passed!")

if __name__ == '__main__':
    asyncio.run(test_rest_mock())
