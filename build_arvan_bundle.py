import os

admin_ui_path = os.path.abspath('backend/worker/src/admin_ui.js')
with open(admin_ui_path, 'r', encoding='utf-8') as f:
    admin_ui_content = f.read()

# Change branding text in header from "سامانه ابری کلودفلر" to "سامانه ابری آروان (ArvanCloud Edge)"
admin_ui_content = admin_ui_content.replace('سامانه ابری کلودفلر', 'سامانه ابری آروان (ArvanCloud Edge)')
admin_ui_content = admin_ui_content.replace('export function getAdminDashboardHtml() {', 'function getAdminDashboardHtml() {')

bundle_code = f"""
// ==========================================
// AsanVPN Dashboard on ArvanCloud Edge Computing
// ==========================================

{admin_ui_content}

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
      pop: request.headers.get('X-Country-Code') || 'IR',
      time: new Date().toISOString()
    }}), {{
      headers: {{ 'content-type': 'application/json; charset=utf-8' }}
    }});
  }}

  // 2. Serve Admin Dashboard UI
  if (path === '/' || path === '/admin' || path === '/dashboard' || path === '/panel') {{
    return new Response(getAdminDashboardHtml(), {{
      headers: {{
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Powered-By': 'ArvanCloud Edge Computing'
      }}
    }});
  }}

  // 3. Proxy API requests to backend
  if (path.startsWith('/api/')) {{
    try {{
      const targetUrl = new URL(url.pathname + url.search, 'https://asanvpn-worker.hi-deploy.workers.dev');
      
      const adminToken = request.headers.get('x-admin-token') || request.headers.get('X-Admin-Token') || '';
      const contentType = request.headers.get('content-type') || 'application/json';

      const proxyHeaders = new Headers();
      proxyHeaders.set('Accept', 'application/json');
      proxyHeaders.set('Content-Type', contentType);
      proxyHeaders.set('User-Agent', 'ArvanCloud-Edge/1.0');
      if (adminToken) {{
        proxyHeaders.set('X-Admin-Token', adminToken);
      }}

      // Clone or read body safely
      let reqBody = undefined;
      if (!['GET', 'HEAD'].includes(request.method)) {{
        reqBody = await request.arrayBuffer();
      }}

      const proxyRequest = new Request(targetUrl.toString(), {{
        method: request.method,
        headers: proxyHeaders,
        body: reqBody,
        redirect: 'follow'
      }});

      const response = await fetch(proxyRequest);
      const respHeaders = new Headers(response.headers);
      respHeaders.set('Access-Control-Allow-Origin', '*');
      respHeaders.set('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token');
      respHeaders.set('X-Served-By', 'ArvanCloud-Edge');

      return new Response(response.body, {{
        status: response.status,
        statusText: response.statusText,
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

out_dir = 'backend/arvan-edge'
os.makedirs(out_dir, exist_ok=True)
bundle_path = os.path.join(out_dir, 'bundle.js')
with open(bundle_path, 'w', encoding='utf-8') as f:
    f.write(bundle_code)

print(f"Generated updated Arvan bundle at {bundle_path}")
