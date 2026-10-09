import random
import threading
from urllib.parse import quote
from .config import COUNTRIES, GATEWAY_HINTS


def is_gw(host):
    if not host:
        return False
    h = host.lower()
    return any(g in h for g in GATEWAY_HINTS)


def split_hp(s):
    if not s:
        return None, None
    s = s.strip()
    if s.startswith("[") and "]" in s:
        e = s.index("]")
        h = s[1:e]
        r = s[e + 1:]
        p = r.lstrip(":") if r.startswith(":") else ""
    elif ":" in s:
        h, _, p = s.rpartition(":")
    else:
        return s, None
    return h.strip(), p


def parse_auth(a):
    if not a:
        return "", ""
    if ":" in a:
        u, _, p = a.partition(":")
        return quote(u.strip(), safe=""), quote(p.strip(), safe="")
    return quote(a.strip(), safe=""), ""


def parse_line(line):
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None
    sch = "http"
    body = raw
    if "://" in raw:
        sch, _, body = raw.partition("://")
        sch = sch.lower()
        if sch not in ("http", "https", "socks4", "socks5", "socks5h"):
            return None
        body = body.strip().lstrip("/")
        if not body:
            return None
    if "@" in body:
        a, _, hp = body.rpartition("@")
    else:
        a, hp = "", body
    h, p = split_hp(hp)
    if not h:
        return None
    if p is None or not p:
        p = "443" if sch == "https" else "80"
    try:
        pn = int(p)
    except ValueError:
        return None
    if not 1 <= pn <= 65535:
        return None
    u, pw = parse_auth(a)
    c = u + ":" + pw + "@" if u else ""
    url = sch + "://" + c + h + ":" + str(pn)
    return {"url": url, "scheme": sch, "host": h, "port": pn,
            "user": u, "pwd": pw, "raw": raw, "gateway": is_gw(h)}


def build(h, ps, u, pw, sch="http"):
    try:
        pn = int(ps)
    except (ValueError, TypeError):
        return None
    if not 1 <= pn <= 65535:
        return None
    h = h.strip()
    if not h:
        return None
    u = quote(u, safe="") if u else ""
    pw = quote(pw, safe="") if pw else ""
    c = u + ":" + pw + "@" if u else ""
    url = sch + "://" + c + h + ":" + str(pn)
    return {"url": url, "scheme": sch, "host": h, "port": pn,
            "user": u, "pwd": pw, "raw": h + ":" + str(pn) + ":" + u + ":" + pw,
            "gateway": is_gw(h)}


def parse_simple(raw):
    raw = (raw or "").strip()
    if not raw or raw.startswith("#"):
        return None
    if "://" in raw:
        return parse_line(raw)
    if "@" in raw:
        return parse_line("http://" + raw)
    parts = raw.split(":")
    if len(parts) == 4:
        if parts[1].isdigit():
            return build(parts[0], parts[1], parts[2], parts[3])
        if parts[3].isdigit():
            return build(parts[2], parts[3], parts[0], parts[1])
    if len(parts) == 2 and parts[1].isdigit():
        return build(parts[0], parts[1], "", "")
    dp = raw.split("-")
    if len(dp) >= 4:
        h = dp[0]
        p = dp[1]
        if p.isdigit():
            u = "-".join(dp[2:-1])
            pw = dp[-1]
            return build(h, p, u, pw)
    return parse_line(raw)


class ProxyManager:
    def __init__(self, max_failures=4):
        self.proxies = []
        self.index = 0
        self.lock = threading.RLock()
        self.failed = {}
        self.max_failures = max_failures

    def load_file(self, path):
        n = 0
        try:
            f = open(path, "r", encoding="utf-8", errors="ignore")
            for line in f:
                p = parse_simple(line)
                if p:
                    if not any(x["raw"] == p["raw"] for x in self.proxies):
                        self.proxies.append(p)
                        n += 1
            f.close()
        except OSError:
            pass
        return n

    def add(self, h, p, u="", pw=""):
        pr = build(h, str(p), u, pw)
        if pr:
            with self.lock:
                self.proxies.append(pr)
        return pr

    def size(self):
        return len(self.proxies)

    def next(self, sid=None):
        with self.lock:
            if not self.proxies:
                return None
            ok = [p for p in self.proxies if self.failed.get(p["raw"], 0) < self.max_failures]
            if not ok:
                self.failed.clear()
                ok = list(self.proxies)
            base = dict(ok[self.index % len(ok)])
            self.index = (self.index + 1) % max(len(ok), 1)
            if sid and base.get("user") and "-session-" not in base.get("user", ""):
                su = base["user"] + "-session-" + sid
                url = base["scheme"] + "://" + su + ":" + base["pwd"] + "@" + base["host"] + ":" + str(base["port"])
                base["url"] = url
                base["user"] = su
                base["sticky_id"] = sid
            return base

    def mark_failed(self, p):
        if not p:
            return
        with self.lock:
            k = p.get("raw")
            if k:
                self.failed[k] = self.failed.get(k, 0) + 1

    def mark_success(self, p):
        if not p:
            return
        with self.lock:
            k = p.get("raw")
            if k and k in self.failed:
                del self.failed[k]

    def stats(self):
        with self.lock:
            t = len(self.proxies)
            d = sum(1 for v in self.failed.values() if v >= self.max_failures)
            return {"total": t, "active": t - d, "dead": d}


def to_req(p):
    if not p:
        return None
    u = p.get("url")
    return {"http": u, "https": u} if u else None
