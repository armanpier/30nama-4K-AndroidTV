with open('backend/vps-server/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

escaped = html.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
js_code = f"""/**
 * Embedded Web Admin Dashboard for AsanVPN
 * Served directly by the Cloudflare Worker at /admin or /
 */

export function getAdminDashboardHtml() {{
  return `{escaped}`;
}}
"""

with open('backend/worker/src/admin_ui.js', 'w', encoding='utf-8') as f:
    f.write(js_code)

print("Successfully generated backend/worker/src/admin_ui.js from dashboard.html!")
