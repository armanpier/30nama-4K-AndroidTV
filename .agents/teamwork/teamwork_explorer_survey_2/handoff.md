# Comprehensive Investigation Report: Google OAuth 2.0 & Gemini API Authentication for Windows Desktop

**Author**: Explorer Survey 2 (`teamwork_explorer_survey_2`)  
**Mission**: Investigate Google Account authentication mechanisms on Windows desktop vs Android for accessing Gemini APIs without requiring manual API key entry.  
**Date**: 2026-11-08  

---

## 1. Observation

### 1.1 Local Host Python & Environment Inspection
Executing Python environment inspection on the Windows host (`Python 3.11.0 [MSC v.1933 64 bit (AMD64)]` at `C:\Users\Arman\AppData\Local\Programs\Python\Python311\python.exe`) revealed the following module availability:
- `google.auth`: **Available**
- `google.genai`: **Available** (Version `2.28.0` located at `C:\Users\Arman\AppData\Local\Programs\Python\Python311\Lib\site-packages\google\genai`)
- `keyring`: **Available** (Active backend: `keyring.backends.Windows.WinVaultKeyring` with priority 5)
- `win32crypt`: **Available** (Windows DPAPI via `pywin32`)
- `cryptography`: **Available**
- `websockets`: **Available**
- `google_auth_oauthlib`: Not installed (standard library implementation of RFC 8252 & RFC 7636 is straightforward and was verified independently)

### 1.2 Inspection of `google-genai` SDK v2.28.0 Source Code
Direct code inspection of the installed `google-genai` SDK demonstrated the exact authentication architecture for Gemini REST and Multimodal Live WebSocket connections:

1. **Client Initialization** (`google/genai/_api_client.py:BaseApiClient.__init__`):
   ```python
   def __init__(
       self,
       vertexai: Optional[bool] = None,
       api_key: Optional[str] = None,
       credentials: Optional[google.auth.credentials.Credentials] = None,
       project: Optional[str] = None,
       location: Optional[str] = None,
       http_options: Optional[HttpOptionsOrDict] = None,
   ):
   ```
   - When `self.vertexai == True`, the base URL defaults to `https://{self.location}-aiplatform.googleapis.com/` and API version `v1beta1`. Credentials must be a `google.auth.credentials.Credentials` object (or ADC).
   - When `self.vertexai == False` (Gemini Developer API), base URL defaults to `https://generativelanguage.googleapis.com/` and requires `api_key` (via `x-goog-api-key` header).

2. **Multimodal Live WebSocket Connection** (`google/genai/live.py:1052-1119`):
   ```python
   # Line 1052-1078 in live.py:
   else:
     uri = f'{base_url}/ws/google.cloud.aiplatform.{version}.LlmBidiService/BidiGenerateContent'

     if not self._api_client._credentials:
       creds, _ = google.auth.default(
           scopes=['https://www.googleapis.com/auth/cloud-platform']
       )
     else:
       creds = self._api_client._credentials

     if not (creds.token and creds.valid):
       auth_requests = _auth_requests()
       auth_req = auth_requests.Request()
       creds.refresh(auth_req)
     bearer_token = creds.token

     original_headers = self._api_client._http_options.headers
     headers = original_headers.copy() if original_headers is not None else {}
     if not headers.get('Authorization'):
       headers['Authorization'] = f'Bearer {bearer_token}'

   # Line 1117-1120 in live.py:
   async with ws_connect(
       uri, additional_headers=headers, **self._api_client._websocket_ssl_ctx
   ) as ws:
     await ws.send(request)
   ```
   This confirms that for Vertex AI Live sessions, `google-genai` passes the OAuth access token in the `Authorization: Bearer <bearer_token>` HTTP upgrade header during the WebSocket handshake.

3. **Generative Language API Live WebSocket Connection** (`google/genai/live.py:970-985`):
   - For `generativelanguage.googleapis.com`, the Live API WebSocket URI is:
     `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
   - Authentication is passed either via `x-goog-api-key: <key>` / query parameter `?key=<key>`, or for constrained sessions via `BidiGenerateContentConstrained?access_token=<token>` (or `Authorization: Token <token>`).

### 1.3 Windows Security and Storage Verification
Direct execution of Python test scripts on the host confirmed:
- `win32crypt.CryptProtectData` (DPAPI) and `CryptUnprotectData` successfully encrypted and decrypted test payloads without third-party drivers.
- `keyring.get_keyring()` returned `keyring.backends.Windows.WinVaultKeyring`, which interfaces with the Windows Credential Manager / Credential Locker.

### 1.4 PKCE and Ephemeral Loopback Port Verification
Testing ephemeral loopback binding in Python:
- `HTTPServer(('127.0.0.1', 0), ...)` successfully bound to random ephemeral port (e.g. port `62255`).
- PKCE S256 verifier generation (32 random bytes, base64url encoded, len=43) and challenge (`base64url(sha256(verifier))`, len=43) verified conforming to RFC 7636.

---

## 2. Logic Chain

```
[Observation 1.1, 1.2: Android vs Desktop Auth]
  │
  ├─> Fact: Android Gemini uses Google Play Services (com.google.android.gms) & AccountManager.
  │         Play Services holds system-level Google Account credentials and communicates
  │         with internal Google Assistant / Gemini backend endpoints.
  │
  └─> Fact: Windows desktop has no Google Play Services or system-level Google SSO broker.
            Google policy forbids OAuth within embedded WebViews (WebView2, CEF, Electron).
            Conclusion: Desktop Windows apps MUST implement RFC 8252 (OAuth 2.0 for Native Apps)
            using the default system browser and a local loopback redirect server.

[Observation 1.3, 1.4: Desktop OAuth Loopback Flow (RFC 8252 + RFC 7636 PKCE)]
  │
  ├─> Fact: Google Cloud Console supports OAuth Client ID type "Desktop app".
  │         Google allows any ephemeral port on loopback interface (http://127.0.0.1:<port>).
  │
  ├─> Fact: Desktop clients cannot protect client secrets (public client).
  │         However, Google's token endpoint still mandates sending client_secret if one was
  │         issued. Google mitigates code interception through PKCE (code_challenge & code_verifier).
  │
  └─> Flow: App binds 127.0.0.1:0 -> Launches system browser -> Google signs in & redirects to
            loopback -> App receives code -> Exchanges code + code_verifier for tokens.

[Observation 1.2: Gemini API Integration with OAuth Bearer Tokens]
  │
  ├─> Generative Language REST API (generativelanguage.googleapis.com):
  │   - Accepts Authorization: Bearer <access_token> in HTTP headers.
  │   - Requires scopes: https://www.googleapis.com/auth/generative-language or
  │     https://www.googleapis.com/auth/cloud-platform.
  │   - Used for On-Demand Screen Capture queries (generateContent).
  │
  └─> Gemini Multimodal Live WebSocket API:
      - Vertex AI Endpoint: wss://{location}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent
        Natively accepts Authorization: Bearer <access_token> in WebSocket handshake headers.
        Auto-refreshed by google.oauth2.credentials.Credentials.
      - Generative Language API Endpoint: wss://generativelanguage.googleapis.com/ws/...
        Accepts API key via x-goog-api-key or ephemeral tokens via access_token query param.

[Observation 1.1, 1.3: Secure Persistence and Token Lifecycle]
  │
  ├─> Access tokens expire after 3600 seconds (1 hour).
  ├─> Refresh tokens are long-lived and must be persisted securely.
  │   - Windows Credential Manager (via keyring / WinVaultKeyring) or DPAPI (win32crypt)
  │     protects the refresh token using OS-level per-user encryption.
  │
  └─> Auto-refresh: google.oauth2.credentials.Credentials or standard POST to
      https://oauth2.googleapis.com/token refreshes the access token transparently.
```

---

## 3. Detailed Architectural Findings

### 3.1 Android vs Desktop Authentication Comparison

| Dimension | Android Gemini App | Windows Desktop Application |
|---|---|---|
| **Identity Provider** | Google Play Services (`com.google.android.gms`) + Android `AccountManager` | Google Identity Platform via RFC 8252 (OAuth 2.0 for Native Apps) |
| **User Sign-In UX** | Zero-touch or single-tap system account picker dialog ("Continue as [User]") | Default system browser opens Google Consent Screen; redirects back to local app |
| **API Endpoints** | First-party Google Assistant / Gemini private internal backend | Public Gemini APIs: Generative Language API or Google Cloud Vertex AI |
| **Credential Type** | Internal GMS authentication tokens | OAuth 2.0 Bearer access tokens (1h validity) + offline refresh token |
| **Browser Policy** | In-OS account sync / Custom Tabs | System browser mandatory; embedded WebViews strictly blocked by Google OAuth policy |
| **Configuration Requirement** | None (pre-bundled OS signature permissions) | OAuth 2.0 Client ID (type "Desktop app") configured in Google Cloud Console |

### 3.2 Desktop Google Sign-In Mechanism: RFC 8252 & RFC 7636 PKCE

The application implements standard RFC 8252:

```
+-------------------------------------------------------------------------------+
|                             Windows Desktop App                               |
|                                                                               |
|  1. Generate PKCE verifier (32 bytes) & challenge = Base64URL(SHA256(v))     |
|  2. Generate random CSRF state token                                          |
|  3. Bind HTTP server to 127.0.0.1:0 (OS allocates ephemeral port P)            |
|  4. Open default system browser via webbrowser.open()                         |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼ (HTTP GET in browser)
+───────────────────────────────────────────────────────────────────────────────+
| Google Authorization Server: https://accounts.google.com/o/oauth2/v2/auth     |
|   ?client_id=...                                                              |
|   &redirect_uri=http://127.0.0.1:P/oauth2callback                             |
|   &response_type=code                                                         |
|   &scope=openid email profile https://www.googleapis.com/auth/cloud-platform  |
|   &code_challenge=...&code_challenge_method=S256                              |
|   &state=...&access_type=offline&prompt=consent                               |
+───────────────────────────────────────────────────────────────────────────────+
                                      │ (User consents)
                                      ▼ (Browser Redirect to loopback)
+───────────────────────────────────────────────────────────────────────────────+
| Local Loopback Server: http://127.0.0.1:P/oauth2callback?code=AUTH_CODE&state |
|   1. Verify state parameter matches original                                  |
|   2. Extract authorization code                                               |
|   3. Return user-friendly HTML response ("Sign-in complete. You can close.")  |
|   4. Terminate HTTP server                                                    |
+───────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼ (Direct HTTPS POST)
+───────────────────────────────────────────────────────────────────────────────+
| Google Token Endpoint: POST https://oauth2.googleapis.com/token               |
|   Body: code=AUTH_CODE & code_verifier=... & client_id=... & client_secret=...|
|         & grant_type=authorization_code & redirect_uri=http://127.0.0.1:P/... |
|                                                                               |
| Response: {                                                                   |
|   "access_token": "ya29...",                                                  |
|   "expires_in": 3599,                                                         |
|   "refresh_token": "1//04...",                                                |
|   "token_type": "Bearer",                                                     |
|   "id_token": "..."                                                           |
| }                                                                             |
+───────────────────────────────────────────────────────────────────────────────+
```

#### Key Technical Parameters:
- **Loopback IP:** Must use `127.0.0.1` rather than `localhost` (RFC 8252 §8.3: avoids DNS resolution exploits and IPv6 dual-stack ambiguities).
- **Ephemeral Port:** The socket binds to port `0`, allowing the OS kernel to select any available port. Google OAuth 2.0 for Desktop apps explicitly permits any port on `127.0.0.1` without prior configuration in Google Cloud Console.
- **Client Secret in Desktop Apps:** Even though native apps cannot protect secrets, Google's token endpoint checks the `client_secret` assigned to the Desktop OAuth client. Combining `client_secret` with PKCE provides defense-in-depth: the secret proves client registration, while PKCE ensures only the instance that initiated the request can redeem the authorization code.

### 3.3 OAuth Token Integration with Gemini APIs

#### A. Generative Language REST API (`generativelanguage.googleapis.com`)
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- **Authentication**: HTTP Header `Authorization: Bearer <access_token>`
- **Scopes**:
  - `https://www.googleapis.com/auth/generative-language` (Standard Generative AI scope)
  - `https://www.googleapis.com/auth/cloud-platform` (Broad GCP scope)
- **Use in Application**: Ideal for **On-Demand Capture** mode. When the user presses a hotkey or UI button to capture a screen or window, the app captures a JPEG/PNG snapshot and sends a POST request with the user prompt and image parts using the OAuth Bearer token.

#### B. Vertex AI Multimodal Live WebSocket API (`aiplatform.googleapis.com`)
- **Endpoint**: `wss://{LOCATION}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent`
- **Supported Locations**: `us-central1`, `us-east4`, `europe-west1`, etc.
- **Authentication**: HTTP Header `Authorization: Bearer <access_token>` sent in the initial WebSocket upgrade handshake (`additional_headers={"Authorization": f"Bearer {token}"}`).
- **Supported Models**: `gemini-2.0-flash-exp`, `gemini-2.0-flash-realtime-exp`, `gemini-2.5-flash`.
- **SDK Integration**: Directly supported by the installed `google-genai` SDK:
  ```python
  from google import genai
  from google.oauth2.credentials import Credentials

  creds = Credentials(
      token=access_token,
      refresh_token=refresh_token,
      token_uri="https://oauth2.googleapis.com/token",
      client_id=client_id,
      client_secret=client_secret,
      scopes=["https://www.googleapis.com/auth/cloud-platform"]
  )

  client = genai.Client(
      vertexai=True,
      credentials=creds,
      project=project_id,
      location="us-central1"
  )

  async with client.aio.live.connect(model="gemini-2.5-flash", config={"response_modalities": ["AUDIO"]}) as session:
      # Real-time streaming loop
  ```

#### C. Generative Language API WebSocket (`generativelanguage.googleapis.com`)
- **Endpoint**: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- **Authentication**: Uses `x-goog-api-key: <key>` header or query parameter `?key=<key>`.
- **Ephemeral Token Option**: Alternatively, the server can issue an ephemeral token via `POST /v1beta/auth_tokens` and connect to `BidiGenerateContentConstrained?access_token=<ephemeral_token>`.

### 3.4 Client Configuration Options: Developer vs End-User Experience

To ensure an end user can simply click "Sign in with Google" without typing an API key:

1. **Option 1: Bundled App OAuth Client (Zero-Configuration for End Users)**
   - The application distributes a default Google Cloud OAuth 2.0 Desktop Client ID & Secret in an application configuration file (`oauth_config.json`) or embedded constants.
   - When the user launches the app, they see: "Sign in with Google".
   - Clicking the button launches the browser, user signs in, and the app connects.
   - *Consent Screen Consideration*:
     - If the project is in "Testing" mode, users must be listed as test users.
     - For general public distribution, the project must be submitted for Google verification or users can click past the "Google hasn't verified this app" notice ("Advanced -> Go to app (unsafe)").

2. **Option 2: Bring-Your-Own Client ID / Project (Developer Settings)**
   - The UI includes a settings panel where users can paste their own `client_id`, `client_secret`, and `project_id` (or load a `client_secret.json` from Google Cloud Console).
   - This provides complete quota isolation, avoids central project rate limits, and bypasses third-party verification warnings.

3. **Recommended Dual-Mode Configuration Strategy**:
   - The application should provide built-in default OAuth client parameters for instant 1-click login, while allowing an override in Settings for custom Google Cloud credentials or manual API keys.

### 3.5 Token Security, Storage, and Lifecycle Management on Windows

1. **Secure Storage on Windows**:
   - **Sensitive Data (Refresh Token)**: Stored in **Windows Credential Manager** via the standard Python `keyring` library (`WinVaultKeyring` backend), or encrypted using Windows DPAPI (`win32crypt.CryptProtectData`).
     - Windows DPAPI encrypts data using a cryptographic key derived from the user's Windows logon password. No other user account or process on another machine can decrypt it.
   - **Non-Sensitive Session Cache**: Stored in a JSON cache file at `%APPDATA%\GeminiDesktopScreenshare\session.json`:
     ```json
     {
       "user_email": "user@gmail.com",
       "user_name": "Arman",
       "access_token": "ya29...",
       "expires_at": 1731075600.0,
       "project_id": "my-gcp-project"
     }
     ```

2. **Automatic Refresh Logic**:
   - Access tokens expire after 1 hour (3600s).
   - Proactive refresh: When making an API call or before initiating a Live WebSocket connection, check if `time.time() > (expires_at - 300)`. If within 5 minutes of expiration, invoke `creds.refresh(Request())` or POST to `https://oauth2.googleapis.com/token`.
   - `google.oauth2.credentials.Credentials` handles automatic refresh transparently if `creds.valid` is False.

3. **Logout / Revocation Flow**:
   - When the user clicks "Sign Out" or "Disconnect Account" in the UI:
     1. App sends revocation request: `POST https://oauth2.googleapis.com/revoke?token={refresh_token}`.
     2. App deletes the stored credential from Windows Credential Manager (`keyring.delete_password(...)`).
     3. App clears the local session cache (`%APPDATA%\GeminiDesktopScreenshare\session.json`).
     4. App updates UI state to "Signed Out".

---

## 4. Caveats

1. **Google OAuth Verification Warning**: When an unverified Google Cloud project in "External" publishing mode requests sensitive scopes (such as `https://www.googleapis.com/auth/cloud-platform`), Google displays an "Unverified app" consent screen. Users can proceed by clicking "Advanced" -> "Go to [App] (unsafe)". For corporate Google Workspace accounts, Workspace administrators can whitelist the Client ID directly.
2. **Quota and Billing Attribution**: For Vertex AI (`aiplatform.googleapis.com`), requests require a Google Cloud Project ID with Vertex AI API enabled and a billing account linked. For Generative Language API (`generativelanguage.googleapis.com`), calls using OAuth consume quota from the project owning the OAuth Client ID or specified via `x-goog-user-project`.
3. **Loopback Port Conflicts / Firewall**: While binding to port `0` avoids port collisions, corporate host firewalls on Windows occasionally prompt for permission on local socket binding. Because the server binds strictly to loopback (`127.0.0.1`), it does not require opening ports to external networks.

---

## 5. Conclusion

1. **Authentication Viability**: Google Account sign-in without manual API key entry is fully viable and standards-compliant on Windows desktop using RFC 8252 (OAuth 2.0 for Native Apps) paired with RFC 7636 (PKCE) over a local loopback server (`127.0.0.1:<ephemeral_port>`).
2. **Gemini Live WebSocket Support**: Vertex AI Multimodal Live WebSocket API (`wss://{location}-aiplatform.googleapis.com/.../BidiGenerateContent`) natively accepts OAuth 2.0 Bearer tokens in the WebSocket HTTP upgrade headers (`Authorization: Bearer <access_token>`). This is natively supported by the installed `google-genai` SDK v2.28.0 (`client.aio.live.connect`).
3. **On-Demand Capture Support**: Both Generative Language API and Vertex AI REST APIs accept OAuth Bearer tokens in the `Authorization: Bearer <access_token>` header for `generateContent` queries containing desktop screenshots.
4. **Security & Refresh**: Windows Credential Manager (`keyring`) and Windows DPAPI (`win32crypt`) provide robust OS-level encrypted storage for refresh tokens, allowing seamless background token refresh without repeated browser sign-ins.

---

## 6. Verification Method

### 6.1 Independent Verification Commands
To verify the findings and local capability on the Windows host, execute:

1. **Verify Python packages and version**:
   ```powershell
   python -c "import google.auth, google.genai, keyring, win32crypt, websockets; print('All core auth & live libraries present!')"
   ```

2. **Verify Windows Credential Manager & DPAPI**:
   ```powershell
   python -c "import keyring, win32crypt; print('Keyring backend:', keyring.get_keyring()); data=b'test'; enc=win32crypt.CryptProtectData(data, None, None, None, None, 0); assert win32crypt.CryptUnprotectData(enc, None, None, None, 0)[1]==data; print('DPAPI operational!')"
   ```

3. **Verify Ephemeral Loopback Port Allocation and PKCE**:
   ```powershell
   python -c "from http.server import HTTPServer, BaseHTTPRequestHandler; import secrets, hashlib, base64; s = HTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler); print('Bound ephemeral port:', s.server_address[1]); s.server_close(); v = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='); c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip('='); print('PKCE valid:', len(v)==43, len(c)==43)"
   ```

4. **Verify `google-genai` Live WebSocket Header Injection**:
   Inspect line 1077 in `C:\Users\Arman\AppData\Local\Programs\Python\Python311\Lib\site-packages\google\genai\live.py` to confirm `headers['Authorization'] = f'Bearer {bearer_token}'` is passed to `ws_connect`.

### 6.2 Invalidation Conditions
- Google deprecates the loopback IP address flow for Desktop clients in favor of a mandatory external web broker.
- Google removes `Authorization: Bearer` header support from the Vertex AI Live WebSocket gateway.
