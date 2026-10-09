import threading
from curl_cffi.requests import Session
from .config import (
    BAM_DEVICE, BAM_PUBLIC, TOKEN, CLIENT_ID, USER_AGENT_SDK, APP_VERSION,
    LOGIN_QUERY, REGISTER_QUERY, EXCHANGE_QUERY, CHECK_QUERY,
)

tls = threading.local()


def sess():
    s = getattr(tls, "session", None)
    if s is None:
        s = Session(verify=True)
        tls.session = s
    return s


def headers(p, token=None):
    tk = TOKEN if token is None else token
    plat = p.get("platform", "javascript/windows/chrome")
    return {
        "Accept": "*/*",
        "Authorization": "Bearer " + tk,
        "User-Agent": p["ua"],
        "Content-Type": "application/json",
        "Host": "disney.api.edge.bamgrid.com",
        "Origin": "https://www.disneyplus.com",
        "Referer": "https://www.disneyplus.com/",
        "X-BAMSDK-Platform-Id": "browser",
        "X-BAMSDK-Client-ID": CLIENT_ID,
        "X-BAMSDK-Platform": plat,
        "X-BAMSDK-Version": USER_AGENT_SDK,
        "X-Application-Version": APP_VERSION,
        "X-DSS-Edge-Accept": "vnd.dss.edge+json; version=2",
    }


def reg_payload(p):
    return {
        "query": REGISTER_QUERY,
        "variables": {"input": {
            "deviceFamily": p.get("device_family", "browser"),
            "applicationRuntime": p.get("app_runtime", "chrome"),
            "deviceProfile": p["os_name"],
            "deviceLanguage": "en-US",
            "attributes": {
                "osDeviceIds": [],
                "manufacturer": p.get("mfg", ""),
                "model": p.get("model"),
                "operatingSystem": p["os_name"],
                "operatingSystemVersion": p["os_ver"],
                "browserName": p.get("app_runtime", "chrome"),
                "browserVersion": p["browser_ver"],
                "brand": p.get("brand", "web")
            },
            "devicePlatformId": "browser"
        }},
        "operationName": "registerDevice"
    }


def register(px, p):
    h = headers(p)
    pl = reg_payload(p)
    imp = p["imp"]
    s = sess()
    try:
        r = s.post(BAM_DEVICE, json=pl, headers=h, proxies=px, timeout=15, impersonate=imp)
        if r.status_code != 200:
            return None, "reg_" + str(r.status_code)
        data = r.json()
        sdk = (data.get("extensions") or {}).get("sdk") or {}
        td = sdk.get("token", {})
        tk = td.get("accessToken", "") if isinstance(td, dict) else ""
        grant = (data.get("data") or {}).get("registerDevice", {}).get("grant", {}) or {}
        ass = grant.get("assertion", "")
        if ass:
            try:
                h2 = headers(p)
                r2 = s.post(BAM_DEVICE, json={
                    "query": EXCHANGE_QUERY,
                    "variables": {"i": {"deviceGrant": ass}},
                    "operationName": "ex"
                }, headers=h2, proxies=px, timeout=15, impersonate=imp)
                ex = (r2.json().get("extensions") or {}).get("sdk") or {}
                ext = ex.get("token", {})
                if isinstance(ext, dict):
                    nt = ext.get("accessToken", "")
                    if nt: tk = nt
            except Exception:
                pass
        if not tk:
            return None, "no_token"
        return tk, None
    except Exception as e:
        return None, str(e)[:50]


def check_mail(mail, tk, px, p):
    h = headers(p, tk)
    s = sess()
    try:
        r = s.post(BAM_PUBLIC, json={
            "operationName": "check",
            "variables": {"email": mail},
            "query": CHECK_QUERY
        }, headers=h, proxies=px, timeout=15, impersonate=p["imp"])
        if r.status_code != 200:
            return None, None, "chk_" + str(r.status_code)
        data = r.json()
        errs = data.get("errors", [])
        if errs:
            return None, errs, None
        ops = ((data.get("data") or {}).get("check") or {}).get("operations", [])
        return ops, None, None
    except Exception as e:
        return None, None, str(e)[:50]


def login(mail, pw, tk, px, p):
    h = headers(p, tk)
    s = sess()
    try:
        r = s.post(BAM_PUBLIC, json={
            "operationName": "login",
            "variables": {"input": {"email": mail, "password": pw}},
            "query": LOGIN_QUERY
        }, headers=h, proxies=px, timeout=20, impersonate=p["imp"])
        if r.status_code != 200:
            return None, "login_" + str(r.status_code)
        return r.json(), None
    except Exception as e:
        return None, str(e)[:50]
