// ==========================================
// AsanVPN Gateway on ArvanCloud Edge Computing
// Dual-Cloud Primary (Cloudflare Worker) & VPS Fallback
// OPSEC Hardened: Stealth Protected Admin Dashboard & Client Bootstrap
// ==========================================

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;

  // 1. Health check endpoint
  if (path === '/health' || path === '/ping') {
    return new Response(JSON.stringify({
      status: 'ok',
      service: 'AsanVPN ArvanCloud Edge Gateway',
      pop: (request.headers.get && request.headers.get('X-Country-Code')) || 'IR',
      time: new Date().toISOString()
    }), {
      headers: { 'content-type': 'application/json; charset=utf-8' }
    });
  }

  // Read cookies and admin key for stealth authorization
  let reqCookie = '';
  try {
    if (request.headers) {
      if (typeof request.headers.get === 'function') {
        reqCookie = request.headers.get('cookie') || request.headers.get('Cookie') || '';
      } else {
        reqCookie = request.headers['cookie'] || request.headers['Cookie'] || '';
      }
    }
  } catch (_) {}

  const queryKey = url.searchParams.get('key') || url.searchParams.get('token') || url.searchParams.get('auth') || '';
  const isAuthorizedAdmin = (queryKey === 'Arman4237340') || reqCookie.includes('asan_edge_auth=Arman4237340');

  // Handle logout
  if (path === '/logout') {
    const respHeaders = new Headers();
    respHeaders.set('Set-Cookie', 'asan_edge_auth=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly');
    respHeaders.set('Location', '/');
    return new Response(null, { status: 302, headers: respHeaders });
  }

  // 2. Admin Dashboard Frontend
  // Serve the luxury web dashboard HTML directly to all visitors of /, /admin, /dashboard, /panel, /portal
  // Authentication is handled inside the dashboard via #login-modal and /api/v1/admin/login
  if (path === '/' || path === '/admin' || path === '/dashboard' || path === '/panel' || path === '/portal') {
    try {
      const vpsDashboardUrl = 'http://95.182.87.115/dashboard';
      const vpsHtmlResp = await fetch(vpsDashboardUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN-Edge/1.0',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
        }
      });
      if (vpsHtmlResp && vpsHtmlResp.status === 200) {
        const respHeaders = new Headers(vpsHtmlResp.headers);
        respHeaders.set('Content-Type', 'text/html; charset=utf-8');
        respHeaders.set('Cache-Control', 'no-cache, no-store, must-revalidate');
        respHeaders.set('X-Served-By', 'ArvanCloud-Edge');
        return new Response(vpsHtmlResp.body, {
          status: 200,
          headers: respHeaders
        });
      }
    } catch (dashErr) {
      console.error('Failed to proxy dashboard from VPS:', dashErr);
    }

    return new Response('Dashboard currently unavailable. Please retry in a few moments.', {
      status: 503,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }

  // 3. Serve High-Speed APK Direct Download (domestic Iranian edge with ABI support)
  if (path === '/download' || path === '/AsanVPN.apk' || path === '/apk' || path.startsWith('/download/')) {
    try {
      const vpsApk = await fetch(`http://95.182.87.115${url.pathname}${url.search}`, {
        method: request.method,
        headers: { 'User-Agent': 'ArvanEdge-Download/1.0', 'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026' }
      });
      if (vpsApk && vpsApk.status === 200) {
        const respHeaders = new Headers(vpsApk.headers);
        respHeaders.set('Access-Control-Allow-Origin', '*');
        respHeaders.set('Cache-Control', 'public, max-age=1800');
        respHeaders.set('X-Served-By', 'ArvanCloud-Edge');
        return new Response(vpsApk.body, {
          status: 200,
          headers: respHeaders
        });
      }
    } catch (e) {}
    return Response.redirect('https://github.com/armanpier/AsanVPN/releases/latest', 302);
  }

  // 4. Proxy API requests with Cloudflare Primary & VPS Fallback
  if (path.startsWith('/api/')) {
    try {
      // OPSEC: Protect Admin API endpoints on domestic edge.
      // Allow if request has valid edge secret, or valid admin token, or authorized admin cookie!
      const edgeSecretHeader = (request.headers.get && (request.headers.get('x-edge-secret') || request.headers.get('X-Edge-Secret'))) || '';
      
      let adminToken = '';
      try {
        if (request.headers) {
          if (typeof request.headers.get === 'function') {
            adminToken = request.headers.get('x-admin-token') || request.headers.get('X-Admin-Token') || '';
          }
          if (!adminToken && request.headers['x-admin-token']) {
            adminToken = request.headers['x-admin-token'];
          }
          if (!adminToken && request.headers['X-Admin-Token']) {
            adminToken = request.headers['X-Admin-Token'];
          }
        }
      } catch (e) {}

      if (!adminToken) {
        adminToken = url.searchParams.get('token') || url.searchParams.get('admin_token') || '';
      }

      if (path.startsWith('/api/v1/admin/')) {
        // Allow login attempts through to VPS
        if (path !== '/api/v1/admin/login') {
          const hasAuthCookie = reqCookie.includes('asan_edge_auth=');
          const hasAdminToken = Boolean(adminToken);
          const hasEdgeSecret = (edgeSecretHeader === 'asanvpn-edge-internal-secret-2026');

          if (!hasAuthCookie && !hasAdminToken && !hasEdgeSecret) {
            return new Response(JSON.stringify({
              error: 'Forbidden',
              message: 'Administrative endpoints require authentication.'
            }), {
              status: 403,
              headers: { 'Content-Type': 'application/json; charset=utf-8' }
            });
          }
        }
      }

      // Preserve connecting client IP to prevent reverse-proxy wide rate limit lockouts
      const clientIp = (request.headers && (
        (typeof request.headers.get === 'function' ? (request.headers.get('ar-real-ip') || request.headers.get('x-real-ip') || request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for')) : (request.headers['ar-real-ip'] || request.headers['x-real-ip'] || request.headers['cf-connecting-ip'] || request.headers['x-forwarded-for']))
      )) || '';
      const cleanClientIp = clientIp.split(',')[0].trim();

      const contentType = (request.headers.get && request.headers.get('content-type')) || 'application/json';

      const outgoingHeaders = {
        'Accept': 'application/json',
        'Content-Type': contentType,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN-Edge/1.0',
        'X-Edge-Secret': 'asanvpn-edge-internal-secret-2026'
      };
      if (adminToken) {
        outgoingHeaders['X-Admin-Token'] = adminToken;
      }
      if (reqCookie) {
        outgoingHeaders['Cookie'] = reqCookie;
      }
      if (cleanClientIp) {
        outgoingHeaders['X-Forwarded-For'] = cleanClientIp;
        outgoingHeaders['CF-Connecting-IP'] = cleanClientIp;
      }

      // Clone or read body safely
      let reqBody = undefined;
      if (!['GET', 'HEAD'].includes(request.method)) {
        reqBody = await request.arrayBuffer();
      }

      const cfUrl = new URL(url.pathname + url.search, 'https://asanvpn-worker.hi-deploy.workers.dev');
      const vpsUrl = new URL(url.pathname + url.search, 'http://95.182.87.115');

      let response = null;
      let lastErr = null;

      const isFromWorker = request.headers.get && (request.headers.get('x-from-worker') === '1' || request.headers.get('X-From-Worker') === '1');

      if (isFromWorker) {
        // Direct to VPS without looping back to Cloudflare
        try {
          response = await fetch(vpsUrl.toString(), {
            method: request.method,
            headers: outgoingHeaders,
            body: reqBody
          });
        } catch (e) {
          throw new Error('Direct VPS fetch failed: ' + e.message);
        }
      } else {
        // 1. Primary: VPS Standalone SQLite (SSOT - Unlimited CPU, instant <2ms response, zero Cloudflare limits)
        try {
          const vpsResp = await fetch(vpsUrl.toString(), {
            method: request.method,
            headers: outgoingHeaders,
            body: reqBody
          });
          if (vpsResp && (vpsResp.status === 200 || vpsResp.status === 201 || vpsResp.status === 204 || vpsResp.status === 400 || vpsResp.status === 403 || vpsResp.status === 404 || vpsResp.status === 429)) {
            response = vpsResp;
          } else {
            lastErr = new Error('VPS returned status ' + (vpsResp ? vpsResp.status : 'null'));
          }
        } catch (e) {
          lastErr = e;
        }

        // 2. Secondary Fallback: Cloudflare Worker (emergency fallback only)
        if (!response) {
          try {
            response = await fetch(cfUrl.toString(), {
              method: request.method,
              headers: outgoingHeaders,
              body: reqBody
            });
          } catch (e) {
            throw new Error('Both VPS and Cloudflare failed: ' + (lastErr ? lastErr.message : '') + ' | ' + e.message);
          }
        }
      }

      const respHeaders = new Headers(response.headers);
      respHeaders.set('Access-Control-Allow-Origin', '*');
      respHeaders.set('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token, X-Edge-Secret');
      respHeaders.set('X-Served-By', 'ArvanCloud-Edge');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: respHeaders
      });
    } catch (err) {
      return new Response(JSON.stringify({
        success: false,
        error: 'Proxy to backend failed: ' + err.message
      }), {
        status: 502,
        headers: { 'content-type': 'application/json; charset=utf-8' }
      });
    }
  }

  return new Response('Not Found', { status: 404 });
}
