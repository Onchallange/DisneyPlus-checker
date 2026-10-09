from datetime import datetime, timezone


def parse(data, cc_hint=""):
    lg = (data.get("data") or {}).get("login") or {}
    errs = data.get("errors", [])

    for e in errs:
        m = str(e.get("message", "")).lower()
        if "bad-credentials" in m:
            return {"status": "INVALID", "info": "bad_credentials"}
        if "password-reset-required" in m or "password_reset_required" in m:
            return {"status": "RESET", "info": "password_reset_required", "country": cc_hint}
        if "otp" in m or "verification" in m:
            return {"status": "OTP", "info": "verification_required"}

    if "password-reset-required" in str(errs).lower():
        return {"status": "RESET", "info": "password_reset_required", "country": cc_hint}

    if not lg:
        return None

    ses = lg.get("activeSession") or {}
    ident = lg.get("identity") or {}
    sub = ident.get("subscriber") or {}
    subs = sub.get("subscriptions") or []
    issub = ses.get("isSubscriber", False)
    ss = (sub.get("subscriberStatus", "") or "").upper()

    cc = "N/A"
    locs = (lg.get("account") or {}).get("attributes", {}).get("locations", {})
    for lk in ("registration", "purchase", "manual"):
        l = locs.get(lk, {})
        if isinstance(l, dict):
            if "country" in l:
                cc = l["country"]; break
            geo = l.get("geoIp", {})
            if "country" in geo:
                cc = geo["country"]; break

    act = None
    for s in subs:
        st = s.get("state", "").upper()
        if st in ("ACTIVE", "ACTIVE_TRIAL", "TRIAL") or s.get("isEntitled"):
            act = s; break
    if not act and subs:
        act = subs[0]

    plan = "Unknown"; exp = "N/A"; dl = -1; nrr = ""; ft = False; part = ""

    if act:
        plan = (act.get("product") or {}).get("name", "Unknown")
        part = (act.get("source") or {}).get("sourceProvider", "")
        t = act.get("term") or {}
        er = t.get("expiryDate") or ""
        nraw = t.get("nextRenewalDate") or ""
        ft = t.get("isFreeTrial", False)
        if er:
            try:
                dt = datetime.fromisoformat(str(er).replace("Z", "+00:00").split(".")[0])
                exp = dt.strftime("%Y-%m-%d")
                dl = (dt.replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)).days
            except Exception:
                exp = str(er)[:10]
        if (not er or exp == "N/A") and nraw:
            try:
                dt = datetime.fromisoformat(str(nraw).replace("Z", "+00:00").split(".")[0])
                exp = dt.strftime("%Y-%m-%d")
                dl = (dt.replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)).days
            except Exception:
                exp = str(nraw)[:10]
        if nraw:
            nrr = str(nraw)[:10]

    if issub or ss in ("ACTIVE", "CURRENT", "SUBSCRIBED"):
        st = "VALID"
    elif ss in ("INACTIVE", "CHURNED", "LAPSED", "EXPIRED", "CANCELLED"):
        st = "EXPIRED"
    elif dl > 0:
        st = "VALID"
    elif subs:
        st = "EXPIRED" if dl < -30 else "VALID"
    else:
        st = "VALID"

    if not act and not issub and not subs:
        return None

    out = {"status": st, "plan": plan, "country": cc, "expires": exp,
           "days_left": dl, "auto_renew": bool(nrr), "next_renewal": nrr,
           "subscriber_status": ss, "is_free_trial": ft, "partner": part}

    sdk = (data.get("extensions") or {}).get("sdk") or {}
    tk = {}
    if isinstance(sdk, dict):
        s = sdk.get("session")
        if isinstance(s, dict):
            tk["id_token"] = s.get("id_token", "")
            tk["access_token"] = s.get("access_token", "")
            tk["refresh_token"] = s.get("refresh_token", "")
        g = sdk.get("grant")
        if isinstance(g, dict):
            tk["assertion"] = g.get("assertion", "")
        adr = sdk.get("accountDelegationRefreshToken")
        if adr:
            tk["delegation_refresh"] = str(adr)
    out["tokens"] = tk
    return out
