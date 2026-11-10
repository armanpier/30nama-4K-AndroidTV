import sys
import urllib.request
import urllib.error
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'
DESKTOP_KEY = 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ'
BASE_URL = 'https://world.hana-api.com/api/v2/action/'

headers_base = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}

def api_call(action, data_dict, api_key, token=None):
    url = BASE_URL + action
    headers = dict(headers_base)
    headers['c-api-key'] = api_key
    if token:
        headers['c-token'] = token
    
    encoded_data = '&'.join(f'{k}={v}' for k, v in data_dict.items()).encode('utf-8') if data_dict else b''
    req = urllib.request.Request(url, data=encoded_data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode('utf-8')
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode('utf-8', errors='replace')
        return {'http_error': e.code, 'raw': raw_err}
    except Exception as e:
        return {'error': str(e)}

def test_token_binding(token):
    print("\n" + "="*50)
    print(f"TESTING WITH c-token: {token}")
    print("="*50)
    
    # 1. Test /action/user with TV Key
    print("\n--> Testing /action/user with TV KEY:")
    resp_user_tv = api_call('user', {}, TV_KEY, token)
    print("User (TV KEY):", resp_user_tv.get('success'), resp_user_tv.get('msg') or f"User: {resp_user_tv.get('result', {}).get('user', {}).get('username')}")
    
    # 2. Test /action/user with Desktop Key
    print("\n--> Testing /action/user with DESKTOP KEY:")
    resp_user_dt = api_call('user', {}, DESKTOP_KEY, token)
    print("User (DESKTOP KEY):", resp_user_dt.get('success'), resp_user_dt.get('msg') or resp_user_dt)
    
    # 3. Test /action/stream with TV Key
    post_id = '722174' # Movie from new releases
    print(f"\n--> Testing /action/stream (post_id={post_id}) with TV KEY:")
    resp_stream_tv = api_call('stream', {'post_id': post_id, 'free_stream': 'false'}, TV_KEY, token)
    print("Stream (TV KEY) success:", resp_stream_tv.get('success'))
    if resp_stream_tv.get('success'):
        qualities = [q.get('quality') for q in resp_stream_tv.get('result', {}).get('medias', [])]
        print("  Available qualities (TV):", qualities)
    else:
        print("  Error:", resp_stream_tv.get('msg') or resp_stream_tv)
        
    # 4. Test /action/stream with Desktop Key
    print(f"\n--> Testing /action/stream (post_id={post_id}) with DESKTOP KEY:")
    resp_stream_dt = api_call('stream', {'post_id': post_id, 'free_stream': 'false'}, DESKTOP_KEY, token)
    print("Stream (DESKTOP KEY) success:", resp_stream_dt.get('success'))
    if resp_stream_dt.get('success'):
        qualities = [q.get('quality') for q in resp_stream_dt.get('result', {}).get('medias', [])]
        print("  Available qualities (DESKTOP):", qualities)
    else:
        print("  Error:", resp_stream_dt.get('msg') or resp_stream_dt)
        
    # Also test stream_servers
    print(f"\n--> Testing /action/stream_servers with DESKTOP KEY:")
    resp_servers_dt = api_call('stream_servers', {}, DESKTOP_KEY, token)
    print("Servers (DESKTOP KEY) success:", resp_servers_dt.get('success'))
    
    # Save results
    with open('binding_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'token': token,
            'user_tv': resp_user_tv,
            'user_desktop': resp_user_dt,
            'stream_tv': resp_stream_tv,
            'stream_desktop': resp_stream_dt,
            'servers_desktop': resp_servers_dt
        }, f, indent=2, ensure_ascii=False)
    print("\nResults saved to binding_results.json!")

if __name__ == '__main__':
    qr_resp = api_call('qrlogin_code', {}, TV_KEY)
    code = qr_resp.get('result', {}).get('code')
    url = qr_resp.get('result', {}).get('url')
    print(f"\n==========================================")
    print(f"ACTIVATION URL: {url}")
    print(f"CODE: {code}")
    print(f"==========================================\n")
    
    with open('current_qr.json', 'w') as f:
        json.dump({'code': code, 'url': url}, f)
        
    print("Polling for token in background (will wait for 300 seconds)...")
    token = None
    start = time.time()
    while time.time() - start < 300:
        resp = api_call('qrlogin_login', {'code': code}, TV_KEY)
        if resp.get('success') and resp.get('result', {}).get('token'):
            token = resp['result']['token']
            print(f"\n[LOGIN DETECTED] c-token: {token}")
            test_token_binding(token)
            break
        time.sleep(2)
        
    if not token:
        print("Polling timed out.")
