import os
import json
import paramiko

html_path = 'backend/vps-server/dashboard.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

js_html_literal = json.dumps(html_content)

bundle_js_code = f"""// ==========================================
// AsanVPN Gateway on ArvanCloud Edge Computing
// Dual-Cloud Primary (Cloudflare Worker) & VPS Fallback
// Zero-Latency Local Edge In-Memory Dashboard & Proxy
// ==========================================

const DASHBOARD_HTML = {js_html_literal};

addEventListener('fetch', event => {{
  event.respondWith(handleRequest(event.request));
}});

async function handleRequest(request) {{
  const url = new URL(request.url);
  const path = url.pathname;

  // 1. Health check endpoint
  if (path === '/health' || path === '/ping') {{
    return new Response(JSON.stringify({{
      status: 'ok',
      service: 'AsanVPN ArvanCloud Edge Gateway',
      pop: (request.headers.get && request.headers.get('X-Country-Code')) || 'IR',
      time: new Date().toISOString()
    }}), {{
      headers: {{ 'content-type': 'application/json; charset=utf-8' }}
    }});
  }}

  // Read cookies and admin key for stealth authorization
  let reqCookie = '';
  try {{
    if (request.headers) {{
      if (typeof request.headers.get === 'function') {{
        reqCookie = request.headers.get('cookie') || request.headers.get('Cookie') || '';
      }} else {{
        reqCookie = request.headers['cookie'] || request.headers['Cookie'] || '';
      }}
    }}
  }} catch (_) {{}}

  // Handle logout
  if (path === '/logout') {{
    const respHeaders = new Headers();
    respHeaders.set('Set-Cookie', 'asan_edge_auth=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly');
    respHeaders.set('Location', '/');
    return new Response(null, {{ status: 302, headers: respHeaders }});
  }}

  // 2. Admin Dashboard Frontend (Fetched live from VPS with edge in-memory fallback)
  if (path === '/' || path === '/admin' || path === '/dashboard' || path === '/panel' || path === '/portal') {{
    try {{
      const vpsResp = await fetch(`http://95.182.87.115${{path === '/' ? '/dashboard' : path}}`, {{
        headers: {{
          'User-Agent': 'ArvanEdge-Dashboard-Proxy',
          'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
        }}
      }});
      if (vpsResp && vpsResp.status === 200) {{
        const html = await vpsResp.text();
        return new Response(html, {{
          status: 200,
          headers: {{
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'X-Served-By': 'ArvanCloud-Edge-Live'
          }}
        }});
      }}
    }} catch (_) {{}}

    return new Response(DASHBOARD_HTML, {{
      status: 200,
      headers: {{
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Served-By': 'ArvanCloud-Edge-Fallback'
      }}
    }});
  }}

  // 3. Serve High-Speed APK Direct Download (Streamed directly via domestic HTTPS)
  if (path === '/download' || path === '/AsanVPN.apk' || path === '/apk' || path.startsWith('/download/')) {{
    const vpsUrl = `http://95.182.87.115${{url.pathname}}${{url.search}}`;
    const outgoingHeaders = {{
      'User-Agent': 'ArvanEdge-APK-Proxy',
      'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
    }};
    const reqRange = request.headers.get && request.headers.get('range');
    if (reqRange) outgoingHeaders['Range'] = reqRange;

    try {{
      const vpsResp = await fetch(vpsUrl, {{
        method: request.method,
        headers: outgoingHeaders
      }});

      const respHeaders = new Headers();
      respHeaders.set('Content-Type', vpsResp.headers.get('content-type') || 'application/vnd.android.package-archive');
      const cl = vpsResp.headers.get('content-length');
      if (cl) respHeaders.set('Content-Length', cl);
      const cr = vpsResp.headers.get('content-range');
      if (cr) respHeaders.set('Content-Range', cr);
      const cd = vpsResp.headers.get('content-disposition') || 'attachment; filename="AsanVPN.apk"';
      respHeaders.set('Content-Disposition', cd);
      respHeaders.set('Accept-Ranges', 'bytes');
      respHeaders.set('Access-Control-Allow-Origin', '*');
      respHeaders.set('Cache-Control', 'public, max-age=3600');
      respHeaders.set('X-Served-By', 'ArvanCloud-Edge');

      return new Response(vpsResp.body, {{
        status: vpsResp.status,
        headers: respHeaders
      }});
    }} catch (e) {{
      return new Response(null, {{
        status: 302,
        headers: {{
          'Location': vpsUrl,
          'Cache-Control': 'no-cache',
          'Access-Control-Allow-Origin': '*'
        }}
      }});
    }}
  }}

  // 4. Proxy API requests
  if (path.startsWith('/api/')) {{
    try {{
      const edgeSecretHeader = (request.headers.get && (request.headers.get('x-edge-secret') || request.headers.get('X-Edge-Secret'))) || '';
      
      let adminToken = '';
      try {{
        if (request.headers) {{
          if (typeof request.headers.get === 'function') {{
            adminToken = request.headers.get('x-admin-token') || request.headers.get('X-Admin-Token') || '';
          }}
          if (!adminToken && request.headers['x-admin-token']) {{
            adminToken = request.headers['x-admin-token'];
          }}
          if (!adminToken && request.headers['X-Admin-Token']) {{
            adminToken = request.headers['X-Admin-Token'];
          }}
        }}
      }} catch (e) {{}}

      if (!adminToken) {{
        adminToken = url.searchParams.get('token') || url.searchParams.get('admin_token') || '';
      }}

      // Admin Endpoints: Direct to VPS SSOT (no loops)
      if (path.startsWith('/api/v1/admin/')) {{
        if (path !== '/api/v1/admin/login') {{
          const hasAuthCookie = reqCookie.includes('asan_edge_auth=');
          const hasAdminToken = Boolean(adminToken);
          const hasEdgeSecret = (edgeSecretHeader === 'asanvpn-edge-internal-secret-2026');

          if (!hasAuthCookie && !hasAdminToken && !hasEdgeSecret) {{
            return new Response(JSON.stringify({{
              error: 'Forbidden',
              message: 'Administrative endpoints require authentication.'
            }}), {{
              status: 403,
              headers: {{ 'Content-Type': 'application/json; charset=utf-8' }}
            }});
          }}
        }}

        const outgoingAdminHeaders = {{
          'Accept': 'application/json',
          'Content-Type': (request.headers.get && request.headers.get('content-type')) || 'application/json',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN-Edge/1.0',
          'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
        }};
        if (adminToken) outgoingAdminHeaders['X-Admin-Token'] = adminToken;
        if (reqCookie) outgoingAdminHeaders['Cookie'] = reqCookie;

        const vpsUrl = new URL(url.pathname + url.search, 'http://95.182.87.115');
        const fetchOpts = {{
          method: request.method,
          headers: outgoingAdminHeaders
        }};
        if (!['GET', 'HEAD'].includes(request.method)) {{
          fetchOpts.body = await request.arrayBuffer();
        }}

        const vpsResp = await fetch(vpsUrl.toString(), fetchOpts);
        const respText = await vpsResp.text();
        const respHeaders = new Headers();
        respHeaders.set('Content-Type', vpsResp.headers.get('content-type') || 'application/json; charset=utf-8');
        respHeaders.set('Access-Control-Allow-Origin', '*');
        respHeaders.set('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token, X-Edge-Secret');
        respHeaders.set('X-Served-By', 'ArvanCloud-Edge');
        const sc = vpsResp.headers.get('set-cookie');
        if (sc) respHeaders.set('Set-Cookie', sc);

        return new Response(respText, {{
          status: vpsResp.status,
          headers: respHeaders
        }});
      }}

      // Client & General APIs (/api/v1/connect, etc.)
      const clientIp = (request.headers && (
        (typeof request.headers.get === 'function' ? (request.headers.get('ar-real-ip') || request.headers.get('x-real-ip') || request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for')) : (request.headers['ar-real-ip'] || request.headers['x-real-ip'] || request.headers['cf-connecting-ip'] || request.headers['x-forwarded-for']))
      )) || '';
      const cleanClientIp = clientIp.split(',')[0].trim();

      const contentType = (request.headers.get && request.headers.get('content-type')) || 'application/json';

      const outgoingHeaders = {{
        'Accept': 'application/json',
        'Content-Type': contentType,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN-Edge/1.0',
        'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
      }};
      if (adminToken) outgoingHeaders['X-Admin-Token'] = adminToken;
      if (reqCookie) outgoingHeaders['Cookie'] = reqCookie;
      if (cleanClientIp) {{
        outgoingHeaders['X-Forwarded-For'] = cleanClientIp;
        outgoingHeaders['CF-Connecting-IP'] = cleanClientIp;
      }}

      const cfUrl = new URL(url.pathname + url.search, 'https://asanvpn-worker.hi-deploy.workers.dev');
      const vpsUrl = new URL(url.pathname + url.search, 'http://95.182.87.115');

      let response = null;
      let lastErr = null;

      const isFromWorker = request.headers.get && (request.headers.get('x-from-worker') === '1' || request.headers.get('X-From-Worker') === '1');

      const clientFetchOpts = {{
        method: request.method,
        headers: outgoingHeaders
      }};
      if (!['GET', 'HEAD'].includes(request.method)) {{
        clientFetchOpts.body = await request.arrayBuffer();
      }}

      if (isFromWorker) {{
        try {{
          response = await fetch(vpsUrl.toString(), clientFetchOpts);
        }} catch (e) {{
          throw new Error('Direct VPS fetch failed: ' + e.message);
        }}
      }} else {{
        try {{
          const vpsResp = await fetch(vpsUrl.toString(), clientFetchOpts);
          if (vpsResp && (vpsResp.status === 200 || vpsResp.status === 201 || vpsResp.status === 204 || vpsResp.status === 400 || vpsResp.status === 401 || vpsResp.status === 403 || vpsResp.status === 404 || vpsResp.status === 429)) {{
            response = vpsResp;
          }} else {{
            lastErr = new Error('VPS returned status ' + (vpsResp ? vpsResp.status : 'null'));
          }}
        }} catch (e) {{
          lastErr = e;
        }}

        if (!response) {{
          try {{
            response = await fetch(cfUrl.toString(), clientFetchOpts);
          }} catch (e) {{
            throw new Error('Both VPS and Cloudflare failed: ' + (lastErr ? lastErr.message : '') + ' | ' + e.message);
          }}
        }}
      }}

      const respHeaders = new Headers();
      const ct = response.headers.get('content-type');
      if (ct) respHeaders.set('Content-Type', ct);
      const sc = response.headers.get('set-cookie');
      if (sc) respHeaders.set('Set-Cookie', sc);
      respHeaders.set('Access-Control-Allow-Origin', '*');
      respHeaders.set('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token, X-Edge-Secret');
      respHeaders.set('X-Served-By', 'ArvanCloud-Edge');

      const respText = await response.text();

      return new Response(respText, {{
        status: response.status,
        headers: respHeaders
      }});
    }} catch (err) {{
      return new Response(JSON.stringify({{
        success: false,
        error: 'Proxy to backend failed: ' + err.message
      }}), {{
        status: 502,
        headers: {{ 'content-type': 'application/json; charset=utf-8' }}
      }});
    }}
  }}

  return new Response('Not Found', {{ status: 404 }});
}}
"""

bundle_path = 'backend/arvan-edge/bundle.js'
with open(bundle_path, 'w', encoding='utf-8') as f:
    f.write(bundle_js_code)

# Deploy to ArvanCloud via VPS
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

key = '12bf58a5-6acd-5f8b-a8af-20ec8f714f6c'
abs_bundle_path = os.path.abspath(bundle_path)

sftp = ssh.open_sftp()
sftp.put(abs_bundle_path, '/tmp/arvan_bundle.js')
sftp.close()

cmd = f"ARVAN_API_KEY='{key}' arvan ec deploy -f /tmp/arvan_bundle.js asanvpn-dashboard"
_, stdout, stderr = ssh.exec_command(cmd)
print("DEPLOY STDOUT:\n", stdout.read().decode())
print("DEPLOY STDERR:\n", stderr.read().decode())

ssh.close()
