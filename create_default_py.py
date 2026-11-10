with open('code_block_29.txt', 'r', encoding='utf-8') as f:
    code = f.read()

# Enhance headers with c-api-key, c-token, etc.
old_hdr = """    if api_key:
        headers["x-api-key"] = api_key
        headers["api-key"] = api_key"""

new_hdr = """    if api_key:
        headers["c-api-key"] = api_key
        headers["x-api-key"] = api_key
        headers["api-key"] = api_key
    headers["c-version-number"] = "3.2.3" """

if old_hdr in code:
    code = code.replace(old_hdr, new_hdr)
    print("Header enhancement applied!")
else:
    print("Could not find old_hdr exact match, checking variation...")

# Replace default TV key and desktop key defaults
code = code.replace('get_setting("tv_api_key")', 'get_setting("tv_api_key", "VdapnkLG9EHsSmF8yeKcb4253RAuN6YX")')
code = code.replace('get_setting("desktop_api_key")', 'get_setting("desktop_api_key", "et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ")')

with open('plugin.video.30nama/default.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Wrote plugin.video.30nama/default.py, length:", len(code))
