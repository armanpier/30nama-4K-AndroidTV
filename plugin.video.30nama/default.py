# -*- coding: utf-8 -*-
import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.join(_CURRENT_DIR, "resources", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import re
import json
import shutil
import zipfile
import socket
import urllib.parse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
BASE_PLUGIN_URL = sys.argv[0] if len(sys.argv) > 0 else "plugin://plugin.video.30nama/"
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ART_PATH = os.path.join(ADDON_PATH, "resources", "art")

USER_AGENT = "tv30nama/3.2.3"
APP_VERSION = "3.2.3"
DEFAULT_TV_KEY = "VdapnkLG9EHsSmF8yeKcb4253RAuN6YX"
DEFAULT_DESKTOP_KEY = "et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ"
API_BASE_URL = "https://world.hana-api.com/api/v2/action"

# Default session token (users configure in settings or via QR login)
DEFAULT_TOKEN = ""

TEMP_SUB_DIR = xbmcvfs.translatePath("special://temp/30nama_subs/")


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)


def check_and_fix_persian_font():
    """Automatically switches Kodi font to Arial based so Persian never renders as squares."""
    try:
        current = xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "method": "Settings.GetSettingValue",
            "params": {"setting": "lookandfeel.font"},
            "id": 1
        }))
        res = json.loads(current).get("result", {})
        if res.get("value") == "Default":
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "lookandfeel.font", "value": "Arial"},
                "id": 1
            }))
            log("Automatically switched Kodi skin font to 'Arial' for proper Persian rendering.")
    except Exception as exc:
        log(f"Font check warning: {exc}")

    check_and_configure_kodi_proxy()


def is_proxy_alive(proxy_url):
    """Fast check whether a proxy host/port is accepting connections."""
    if not proxy_url:
        return False
    try:
        parsed = urllib.parse.urlparse(proxy_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 10808
        s = socket.create_connection((host, port), timeout=1.2)
        s.close()
        return True
    except Exception:
        return False


def check_and_configure_kodi_proxy():
    """Ensures Kodi's native curl player routes video streams through the proxy only if proxy is alive."""
    try:
        proxy = get_setting("proxy_url")
        active_proxy = None
        if proxy and is_proxy_alive(proxy):
            active_proxy = proxy
        elif not proxy and is_proxy_alive("http://127.0.0.1:10808"):
            active_proxy = "http://127.0.0.1:10808"

        if active_proxy:
            parsed = urllib.parse.urlparse(active_proxy)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 10808
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "network.usehttpproxy", "value": True},
                "id": 1
            }))
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "network.httpproxyserver", "value": host},
                "id": 1
            }))
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "network.httpproxyport", "value": port},
                "id": 1
            }))
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "network.httpproxytype", "value": 0},
                "id": 1
            }))
            log(f"Kodi HTTP proxy enabled: {host}:{port}")
        else:
            # Disable Kodi internal HTTP proxy to allow direct streaming and Android TUN/VPN routing
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": "network.usehttpproxy", "value": False},
                "id": 1
            }))
    except Exception as exc:
        log(f"Proxy check warning: {exc}")


def get_setting(key, default=""):
    val = ADDON.getSetting(key)
    return val.strip() if val else default


def build_url(query):
    return f"{BASE_PLUGIN_URL}?{urllib.parse.urlencode(query)}"


def get_art(name):
    p = os.path.join(ART_PATH, name)
    return p if os.path.exists(p) else ""


def ensure_clean_sub_dir():
    if os.path.exists(TEMP_SUB_DIR):
        shutil.rmtree(TEMP_SUB_DIR, ignore_errors=True)
    os.makedirs(TEMP_SUB_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# API CLIENT (Using requests Session)
# ---------------------------------------------------------------------------

def get_session(use_desktop_key=False):
    session = requests.Session()
    proxy = get_setting("proxy_url")
    if proxy and is_proxy_alive(proxy):
        session.proxies = {"http": proxy, "https": proxy}
    elif not proxy and is_proxy_alive("http://127.0.0.1:10808"):
        session.proxies = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}

    api_key = get_setting("desktop_api_key", DEFAULT_DESKTOP_KEY) if use_desktop_key else get_setting("tv_api_key", DEFAULT_TV_KEY)
    c_token = get_setting("c_token") or DEFAULT_TOKEN

    session.headers.update({
        "User-Agent": USER_AGENT,
        "c-api-key": api_key,
        "c-version-number": APP_VERSION,
        "c-language": "fa",
    })
    if c_token:
        session.headers["c-token"] = c_token
        session.headers["Authorization"] = f"Bearer {c_token}"

    return session, api_key, c_token


def api_request(action_path, params=None, method="GET", use_desktop_key=False):
    session, api_key, c_token = get_session(use_desktop_key=use_desktop_key)
    url = f"{API_BASE_URL}/{action_path.lstrip('/')}"

    # First attempt (uses proxy if configured & responsive)
    try:
        if method.upper() == "POST":
            resp = session.post(url, data=params or {}, timeout=12, verify=False)
        else:
            resp = session.get(url, params=params or {}, timeout=12, verify=False)
        return resp.json()
    except Exception as exc:
        log(f"API attempt failed for {url}: {exc}", xbmc.LOGWARNING)

    # Automatic fallback: if proxy was used and failed, retry directly
    if session.proxies:
        try:
            log(f"Retrying API directly without proxy for {url}...", xbmc.LOGINFO)
            direct_s = requests.Session()
            direct_s.headers.update(session.headers)
            if method.upper() == "POST":
                resp = direct_s.post(url, data=params or {}, timeout=12, verify=False)
            else:
                resp = direct_s.get(url, params=params or {}, timeout=12, verify=False)
            return resp.json()
        except Exception as exc2:
            log(f"Direct API retry failed for {url}: {exc2}", xbmc.LOGWARNING)

    return None


# ---------------------------------------------------------------------------
# SUBTITLE ENGINE (Unzip + CP1256 to UTF-8 + Auto-Attach)
# ---------------------------------------------------------------------------

def is_persian_text(text):
    return bool(re.search(r"[\u0600-\u06FF]", text))


def convert_sub_to_utf8(file_path):
    if get_setting("auto_fix_persian_encoding", "true").lower() != "true":
        return file_path
    try:
        with open(file_path, "rb") as f:
            raw = f.read()

        if raw.startswith(b"\xef\xbb\xbf"):
            text = raw.decode("utf-8-sig")
        elif raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            text = raw.decode("utf-16")
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("cp1256", errors="replace")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as exc:
        log(f"Subtitle UTF-8 conversion warning on {file_path}: {exc}", xbmc.LOGWARNING)
    return file_path


def classify_subtitle_language(file_path):
    fname = os.path.basename(file_path).lower()
    if any(tag in fname for tag in [".fa.", "_fa.", "persian", "farsi", "per."]):
        return "fa"
    if any(tag in fname for tag in [".en.", "_en.", "english", "eng."]):
        return "en"
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
            return "fa" if is_persian_text(sample) else "en"
    except Exception:
        return "other"


def fetch_and_prepare_subtitles(sub_urls):
    if not sub_urls:
        return []

    ensure_clean_sub_dir()
    session, _, _ = get_session(use_desktop_key=False)
    extracted_files = []

    for idx, sub_url in enumerate(sub_urls):
        if not sub_url:
            continue
        try:
            resp = session.get(sub_url, timeout=15, verify=False)
            if resp.status_code != 200:
                continue
            content = resp.content

            lower_url = sub_url.lower().split("?")[0]
            if lower_url.endswith(".zip") or content[:4] == b"PK\x03\x04":
                zip_path = os.path.join(TEMP_SUB_DIR, f"sub_{idx}.zip")
                with open(zip_path, "wb") as zf:
                    zf.write(content)

                with zipfile.ZipFile(zip_path, "r") as archive:
                    for member in archive.namelist():
                        if member.lower().endswith((".srt", ".ass", ".ssa", ".vtt", ".sub")):
                            safe_name = os.path.basename(member)
                            if not safe_name:
                                continue
                            target_path = os.path.join(TEMP_SUB_DIR, f"{idx}_{safe_name}")
                            with open(target_path, "wb") as out_f:
                                out_f.write(archive.read(member))
                            convert_sub_to_utf8(target_path)
                            extracted_files.append(target_path)
            else:
                ext = ".srt"
                for candidate in (".srt", ".ass", ".vtt"):
                    if lower_url.endswith(candidate):
                        ext = candidate
                        break
                target_path = os.path.join(TEMP_SUB_DIR, f"sub_track_{idx}{ext}")
                with open(target_path, "wb") as out_f:
                    out_f.write(content)
                convert_sub_to_utf8(target_path)
                extracted_files.append(target_path)
        except Exception as exc:
            log(f"Failed downloading subtitle {sub_url}: {exc}", xbmc.LOGWARNING)

    fa_subs, en_subs, other_subs = [], [], []
    for path in extracted_files:
        lang = classify_subtitle_language(path)
        base, ext = os.path.splitext(path)
        if not base.endswith(f".{lang}") and lang in ("fa", "en"):
            new_path = f"{base}.{lang}{ext}"
            try:
                os.replace(path, new_path)
                path = new_path
            except OSError:
                pass
        if lang == "fa":
            fa_subs.append(path)
        elif lang == "en":
            en_subs.append(path)
        else:
            other_subs.append(path)

    persian_first = get_setting("sub_priority", "0") == "0"
    return (fa_subs + en_subs + other_subs) if persian_first else (en_subs + fa_subs + other_subs)


def format_kodi_playable_url(raw_url):
    if "|" in raw_url:
        return raw_url
    c_token = get_setting("c_token") or DEFAULT_TOKEN
    headers = {"User-Agent": USER_AGENT}
    if c_token:
        headers["Cookie"] = f"c-token={c_token}"
    encoded = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in headers.items())
    return f"{raw_url}|{encoded}"


# ---------------------------------------------------------------------------
# MENUS & BROWSING (30nama Sleek Interface)
# ---------------------------------------------------------------------------

def list_main_menu():
    check_and_fix_persian_font()
    xbmcplugin.setPluginCategory(HANDLE, "۳۰نما | 30NAMA 4K")
    xbmcplugin.setContent(HANDLE, "videos")

    default_fanart = get_art("fanart.jpg")

    categories = [
        ("جدیدترین‌ها (New Releases)", {"action": "browse_section", "section": "new_releases"}, "new_releases.png",
         "مشاهده و پخش آخرین فیلم‌ها و سریال‌های اضافه شده به آرشیو ۳۰نما با بالاترین کیفیت و زیرنویس هماهنگ فارسی."),
        ("فیلم‌های سینمایی (Movies)", {"action": "browse_section", "section": "movies"}, "movies.png",
         "آرشیو کامل فیلم‌های سینمایی برتر تاریخ سینمای جهان و عناوین روز با کیفیت‌های Bluray، 1080p و 4K Ultra HD."),
        ("سریال‌های برتر (Series)", {"action": "browse_section", "section": "series"}, "series.png",
         "فهرست کامل مجموعه‌های تلویزیونی به تفکیک فصل و قسمت همراه با استریم فوق‌سریع و بدون وقفه."),
        ("۱۰ عنوان برتر (Top 10)", {"action": "browse_section", "section": "top_10"}, "top_10.png",
         "پربازدیدترین و محبوب‌ترین فیلم‌ها و سریال‌های هفته بر اساس آمار و امتیاز کاربران وب‌سایت ۳۰نما."),
        ("پیشنهادهای ویژه (Suggested)", {"action": "browse_section", "section": "suggested"}, "suggested.png",
         "عناوین منتخب و شاهکارهای سینمایی دست‌چین شده توسط تیم تحریریه و منتقدان ۳۰نما."),
        ("جستجوی فیلم و سریال (Search)", {"action": "search"}, "search.png",
         "جستجوی پیشرفته و هوشمند در میان ده‌ها هزار عنوان فیلم، سریال و انیمیشن بر اساس نام فارسی یا انگلیسی."),
        ("پخش مستقیم لینک دانلود 4K (.mkv / .mp4)", {"action": "direct_url"}, "direct_url.png",
         "پخش فوری انواع لینک‌های مستقیم MKV یا MP4 با شتاب‌دهنده سخت‌افزاری و دریافت خودکار زیرنویس."),
        ("حساب کاربری و وضعیت اشتراک (Account)", {"action": "account_info"}, "account.png",
         "مشاهده مشخصات کاربری، نوع اشتراک فعال طلایی (VIP)، تاریخ انقضا و وضعیت اعتبار در سرویس ۳۰نما."),
        ("ورود با کد تلویزیون (QR / Code Login)", {"action": "qr_login"}, "account.png",
         "اتصال سریع حساب کاربری ۳۰نما به تلویزیون هوشمند با اسکن بارکد QR یا وارد کردن کد ۶ رقمی."),
        ("تنظیمات افزونه (Settings)", {"action": "open_settings"}, "settings.png",
         "شخصی‌سازی زبان اولویت زیرنویس، تنظیم پروکسی، انتخاب کیفیت پیش‌فرض و پیکربندی شبکه."),
    ]

    for title, query, art_name, desc in categories:
        art_file = get_art(art_name)
        li = xbmcgui.ListItem(label=title)
        li.setArt({
            "poster": art_file,
            "thumb": art_file,
            "icon": art_file,
            "fanart": default_fanart,
        })
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setPlot(desc)
        li.setInfo("video", {"title": title, "plot": desc})
        xbmcplugin.addDirectoryItem(
            handle=HANDLE,
            url=build_url(query),
            listitem=li,
            isFolder=(query.get("action") in ["browse_section", "search"])
        )

    xbmcplugin.endOfDirectory(HANDLE)


def render_posts_list(posts, category_title="30nama"):
    """Renders movies and series in full poster cards with complete metadata."""
    default_fanart = get_art("fanart.jpg")

    for p in posts:
        post_id = str(p.get("id"))
        title_obj = p.get("title", {})
        title_en = title_obj.get("english") or f"Post {post_id}"
        title_fa = title_obj.get("local")

        # Format bilingual display label
        if title_fa and title_fa != title_en:
            display_label = f"{title_fa} ({title_en})"
        else:
            display_label = title_en

        # Artwork
        img_obj = p.get("image", {})
        poster_obj = img_obj.get("poster", {})
        poster = ""
        if isinstance(poster_obj, dict):
            webp = poster_obj.get("webp", {})
            jpg = poster_obj.get("jpg", {})
            poster = webp.get("large") or webp.get("medium") or jpg.get("large") or ""

        cover_obj = img_obj.get("cover", {})
        fanart = ""
        if isinstance(cover_obj, dict):
            fanart = cover_obj.get("webp") or cover_obj.get("jpg") or poster or default_fanart
        if not fanart:
            fanart = default_fanart

        # Plot / Synopsis
        plot_obj = p.get("plot", {})
        plot = ""
        if isinstance(plot_obj, dict):
            plot = plot_obj.get("local") or plot_obj.get("english") or ""
        elif isinstance(plot_obj, str):
            plot = plot_obj

        # Score / Rating
        score_val = 0.0
        try:
            score_val = float(p.get("score", {}).get("imdb", {}).get("score", 0))
        except Exception:
            pass

        # Info: Year, Duration, Genres
        info_obj = p.get("info", {})
        year = info_obj.get("year")
        time_obj = info_obj.get("time", {})
        duration_mins = time_obj.get("default") if isinstance(time_obj, dict) else None

        genres_list = [g.get("name") for g in p.get("genre", []) if isinstance(g, dict) and g.get("name")]

        li = xbmcgui.ListItem(label=display_label)
        li.setArt({
            "poster": poster,
            "thumb": poster,
            "icon": poster,
            "fanart": fanart,
        })

        # Set VideoInfoTag (Kodi 20+)
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(display_label)
        if plot:
            info_tag.setPlot(plot)
        if score_val > 0:
            info_tag.setRating(score_val)
        if year:
            try:
                info_tag.setYear(int(year))
                info_tag.setPremiered(str(year))
            except Exception:
                pass
        if duration_mins:
            try:
                info_tag.setDuration(int(duration_mins) * 60)
            except Exception:
                pass
        if genres_list:
            info_tag.setGenres(genres_list)
        info_tag.setMediaType("movie")

        # Fallback classic setInfo
        info_dict = {
            "title": display_label,
            "originaltitle": title_en,
            "plot": plot,
            "rating": score_val,
            "mediatype": "movie",
        }
        if year:
            try:
                info_dict["year"] = int(year)
            except Exception:
                pass
        if duration_mins:
            try:
                info_dict["duration"] = int(duration_mins) * 60
            except Exception:
                pass
        if genres_list:
            info_dict["genre"] = " / ".join(genres_list)

        li.setInfo("video", info_dict)

        url = build_url({
            "action": "list_streams",
            "id": post_id,
            "title": title_en,
            "poster": poster,
            "fanart": fanart,
            "plot": (plot[:350] if plot else ""),
        })
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

    # Set InfoWall view mode automatically (View 54 in Estuary / 51 in Poster skins)
    try:
        xbmc.executebuiltin("Container.SetViewMode(54)")
    except Exception:
        pass


def browse_section(section_name="new_releases"):
    check_and_fix_persian_font()
    xbmcplugin.setPluginCategory(HANDLE, section_name)
    xbmcplugin.setContent(HANDLE, "movies")

    data = api_request("home", method="GET", use_desktop_key=False)
    if not data or not data.get("success"):
        xbmcgui.Dialog().notification("۳۰نما", "خطا در دریافت لیست فیلم‌ها", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    sec_data = data.get("result", {}).get(section_name, {})
    posts = sec_data.get("posts", []) if isinstance(sec_data, dict) else []

    if not posts:
        xbmcgui.Dialog().notification("۳۰نما", "موردی یافت نشد", xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    render_posts_list(posts, category_title=section_name)


def search_content():
    """Interactive search with Kodi OSK keyboard."""
    check_and_fix_persian_font()
    dialog = xbmcgui.Dialog()
    query = dialog.input("جستجوی فیلم یا سریال در ۳۰نما (Search):", type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        return

    xbmcplugin.setPluginCategory(HANDLE, f"جستجو: {query}")
    xbmcplugin.setContent(HANDLE, "movies")

    pDialog = xbmcgui.DialogProgress()
    pDialog.create("۳۰نما", f"در حال جستجو برای: {query}...")

    data = api_request("search", params={"query": query}, method="POST", use_desktop_key=False)
    pDialog.close()

    if not data or not data.get("success"):
        dialog.notification("۳۰نما", "خطا در برقراری ارتباط با سرور", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    posts = data.get("result", {}).get("posts", [])
    if not posts:
        dialog.ok("۳۰نما", f"هیچ نتیجه‌ای برای '{query}' یافت نشد.")
        xbmcplugin.endOfDirectory(HANDLE)
        return

    render_posts_list(posts, category_title=f"Search: {query}")


def show_account_info():
    """Displays user profile and subscription details."""
    check_and_fix_persian_font()
    user_res = api_request("user", method="GET", use_desktop_key=False)
    if user_res and user_res.get("success"):
        u = user_res.get("result", {}).get("user", {})
        username = u.get("username", "کاربر ۳۰نما")
        email = u.get("email", "")
        plan = u.get("plan", {}).get("title", "طلایی (Golden)")
        expire = u.get("expire_date", "نامشخص")
        msg = (
            f"نام کاربری: {username}\n"
            f"ایمیل: {email}\n"
            f"نوع اشتراک: {plan}\n"
            f"تاریخ انقضا: {expire}\n\n"
            f"وضعیت اتصال: متصل و فعال برای استریم و دانلود 4K"
        )
        xbmcgui.Dialog().ok("حساب کاربری ۳۰نما", msg)
    else:
        xbmcgui.Dialog().notification("۳۰نما", "خطا در دریافت اطلاعات حساب", xbmcgui.NOTIFICATION_WARNING, 3000)


def list_streams_for_movie(post_id, title="", poster="", fanart="", plot=""):
    check_and_fix_persian_font()
    xbmcplugin.setPluginCategory(HANDLE, title or "انتخاب کیفیت و پخش 4K")
    xbmcplugin.setContent(HANDLE, "videos")

    streams = []
    sub_urls = []

    # 1. Fetch direct download links via backend /action/download
    dl_res = api_request("download", params={"post_id": post_id, "free_download": "false"}, method="POST", use_desktop_key=False)
    if dl_res and dl_res.get("success"):
        res_dl = dl_res.get("result", {})
        dl_obj = res_dl.get("download") if isinstance(res_dl, dict) else res_dl

        # Movies: direct list of releases
        if isinstance(dl_obj, list):
            for f in dl_obj:
                dl_url = f.get("dl") or f.get("link") or f.get("url")
                if not dl_url or not isinstance(dl_url, str):
                    continue
                q = str(f.get("quality") or "Direct DL")
                sz = str(f.get("size") or "")
                res_str = str(f.get("resolution") or "")
                enc = str(f.get("encoder") or "")
                is_4k = "2160" in res_str or "4k" in q.lower() or "2160" in q.lower() or "remux" in q.lower()
                tag = "⭐ [4K ULTRA HD]" if is_4k else f"[{q}]"
                label = f"{tag} {q} ({sz}) {enc}".strip()
                streams.append({"label": label, "url": dl_url, "quality": q, "is_4k": is_4k})

                sub = f.get("persian_subtitle")
                if sub and isinstance(sub, str) and sub not in sub_urls:
                    sub_urls.append(sub)

        # Series: dictionary of seasons
        elif isinstance(dl_obj, dict):
            for season_key, releases in dl_obj.items():
                if not isinstance(releases, list):
                    continue
                for rel in releases:
                    q = str(rel.get("quality") or "")
                    sz = str(rel.get("size") or "")
                    is_4k = "2160" in q.lower() or "4k" in q.lower()
                    tag = "⭐ [4K ULTRA HD]" if is_4k else f"[{q}]"
                    links = rel.get("link", [])
                    if isinstance(links, list):
                        for ep in links:
                            ep_num = ep.get("episode", 1)
                            dl_url = ep.get("dl")
                            if dl_url:
                                label = f"{tag} {season_key.upper()} E{ep_num:02d} - {q} ({sz})"
                                streams.append({"label": label, "url": dl_url, "quality": q, "is_4k": is_4k})
                                sub = ep.get("persian_subtitle")
                                if sub and isinstance(sub, str) and sub not in sub_urls:
                                    sub_urls.append(sub)

    # 2. Fetch online stream profiles from /action/stream
    stream_res = api_request("stream", params={"post_id": post_id, "free_stream": "false"}, method="POST", use_desktop_key=False)
    if stream_res and stream_res.get("success"):
        res = stream_res.get("result", {})
        medias = res.get("medias", [])
        for m in medias:
            quality = str(m.get("quality") or "Auto")
            file_obj = m.get("file", {})
            url = file_obj.get("m3u8") or file_obj.get("url") or file_obj.get("mp4")
            if url:
                label = f"[{quality} پخش آنلاین] HLS Stream"
                is_4k = "2160" in quality.lower() or "4k" in quality.lower()
                streams.append({"label": label, "url": url, "quality": quality, "is_4k": is_4k})

        raw_subs = res.get("subtitles", [])
        for s in raw_subs:
            s_url = s.get("url") if isinstance(s, dict) else str(s)
            if s_url and s_url not in sub_urls:
                sub_urls.append(s_url)

    # 3. Check for external subtitles via /action/single
    single_res = api_request("single", params={"post_id": post_id}, method="POST", use_desktop_key=False)
    if single_res and single_res.get("success"):
        subs = single_res.get("result", {}).get("subtitle") or []
        if isinstance(subs, list):
            for s in subs:
                if isinstance(s, dict):
                    s_link = s.get("link") or s.get("url")
                    if s_link and s_link not in sub_urls:
                        sub_urls.append(s_link)

    if not streams:
        msg = dl_res.get("msg") if dl_res else "لینکی برای این عنوان یافت نشد."
        xbmcgui.Dialog().ok("۳۰نما", f"عدم دسترسی به لینک‌ها:\n{msg}")
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Sort 4K releases to the top
    def sort_key(item):
        if item.get("is_4k"):
            return 0
        q = (item.get("quality", "") + " " + item.get("label", "")).lower()
        if "1080" in q:
            return 1
        elif "720" in q:
            return 2
        return 3

    streams.sort(key=sort_key)
    subs_json = json.dumps(sub_urls)

    default_fanart = get_art("fanart.jpg")
    for s in streams:
        li = xbmcgui.ListItem(label=s["label"])
        art_map = {}
        if poster:
            art_map.update({"poster": poster, "thumb": poster, "icon": poster})
        art_map["fanart"] = fanart or default_fanart
        li.setArt(art_map)
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(s["label"])
        if plot:
            info_tag.setPlot(plot)
        info_tag.setMediaType("video")
        li.setProperty("IsPlayable", "true")

        play_url = build_url({
            "action": "play",
            "video_url": s["url"],
            "subs": subs_json,
            "title": title or s["label"],
        })
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=play_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)


def play_stream(video_url, subs_json="[]", title="Video"):
    try:
        sub_urls = json.loads(subs_json) if subs_json else []
    except Exception:
        sub_urls = []

    local_subs = fetch_and_prepare_subtitles(sub_urls)
    playable_path = format_kodi_playable_url(video_url)

    play_item = xbmcgui.ListItem(label=title, path=playable_path)
    info_tag = play_item.getVideoInfoTag()
    info_tag.setTitle(title)

    if ".m3u8" in video_url.lower():
        play_item.setMimeType("application/vnd.apple.mpegurl")
    elif ".mp4" in video_url.lower():
        play_item.setMimeType("video/mp4")
    else:
        play_item.setMimeType("video/x-matroska")

    if local_subs:
        play_item.setSubtitles(local_subs)
        xbmcgui.Dialog().notification(
            "زیرنویس آماده شد",
            f"{len(local_subs)} فایل زیرنویس متصل گردید",
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )

    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def prompt_direct_url():
    check_and_fix_persian_font()
    dialog = xbmcgui.Dialog()
    target = dialog.input("آدرس لینک مستقیم فیلم (MKV / MP4 / M3U8):", type=xbmcgui.INPUT_ALPHANUM)
    if not target:
        return
    sub_url = dialog.input("اختیاری: آدرس فایل زیرنویس (.zip یا .srt):", type=xbmcgui.INPUT_ALPHANUM)
    subs_list = [sub_url] if sub_url else []
    local_subs = fetch_and_prepare_subtitles(subs_list)
    playable_path = format_kodi_playable_url(target)
    li = xbmcgui.ListItem(label="4K Direct Stream", path=playable_path)
    if local_subs:
        li.setSubtitles(local_subs)
    xbmc.Player().play(playable_path, li)


def perform_qr_login():
    check_and_fix_persian_font()
    data = api_request("qrlogin_code", method="POST", use_desktop_key=False)
    if not data or not data.get("success"):
        err = data.get("msg") if isinstance(data, dict) and data.get("msg") else "عدم برقراری ارتباط با سرور. لطفاً اتصال اینترنت خود را بررسی نمایید."
        xbmcgui.Dialog().ok("خطا در ورود", f"خطا در ایجاد کد ورود تلویزیون:\n{err}")
        return

    res = data.get("result", {})
    code = res.get("code")
    url = res.get("url") or f"https://30nama.com/auth/{code}"

    pDialog = xbmcgui.DialogProgress()
    pDialog.create(
        "ورود با تلویزیون - ۳۰نما",
        f"کد ورود شما: [COLOR gold][B]{code}[/B][/COLOR]\n"
        f"در گوشی باز کنید: [COLOR lightblue][B]{url}[/B][/COLOR]\n"
        "پس از باز کردن لینک، روی «فعال‌سازی» در گوشی بزنید..."
    )

    import time
    start_time = time.time()
    token = None

    while time.time() - start_time < 180:
        if pDialog.iscanceled():
            break
        percent = int(((time.time() - start_time) / 180) * 100)
        pDialog.update(percent)

        chk = api_request("qrlogin_login", params={"auth_code": code}, method="POST", use_desktop_key=False)
        if chk and chk.get("success") and chk.get("result", {}).get("token"):
            token = chk["result"]["token"]
            break
        time.sleep(2)

    pDialog.close()

    if token:
        ADDON.setSetting("c_token", str(token))
        xbmcgui.Dialog().ok("ورود موفقیت‌آمیز", "ورود شما با موفقیت تأیید شد و اشتراک VIP فعال گردید!")
        xbmc.executebuiltin("Container.Refresh")
    else:
        xbmcgui.Dialog().notification("ورود", "زمان انتظار به پایان رسید یا لغو شد.", xbmcgui.NOTIFICATION_WARNING, 3000)


def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get("action")

    if not action:
        list_main_menu()
    elif action == "browse_section":
        browse_section(params.get("section", "new_releases"))
    elif action == "search":
        search_content()
    elif action == "account_info":
        xbmcplugin.endOfDirectory(HANDLE, False)
        show_account_info()
    elif action == "list_streams":
        list_streams_for_movie(
            post_id=params.get("id", ""),
            title=params.get("title", ""),
            poster=params.get("poster", ""),
            fanart=params.get("fanart", ""),
            plot=params.get("plot", ""),
        )
    elif action == "play":
        play_stream(
            video_url=params.get("video_url", ""),
            subs_json=params.get("subs", "[]"),
            title=params.get("title", "Video"),
        )
    elif action == "direct_url":
        xbmcplugin.endOfDirectory(HANDLE, False)
        prompt_direct_url()
    elif action == "qr_login":
        xbmcplugin.endOfDirectory(HANDLE, False)
        perform_qr_login()
    elif action == "open_settings":
        xbmcplugin.endOfDirectory(HANDLE, False)
        ADDON.openSettings()


if __name__ == "__main__":
    router(sys.argv[2][1:] if len(sys.argv) > 2 else "")
