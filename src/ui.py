import os
import sys
import threading
from colorama import Fore, Style, init

init(autoreset=True)

CR = Style.RESET_ALL
CV = Fore.LIGHTGREEN_EX
CE = Fore.LIGHTYELLOW_EX
CO = Fore.LIGHTCYAN_EX
CI = Fore.LIGHTRED_EX
CU = Fore.LIGHTBLACK_EX
CX = Fore.LIGHTRED_EX
CINFO = Fore.LIGHTBLUE_EX
CH = Fore.LIGHTMAGENTA_EX
CD = Fore.LIGHTBLACK_EX
CB = Style.BRIGHT
CRS = Fore.LIGHTYELLOW_EX

_lk = threading.Lock()


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print()
    print(CH + CB + "  disney+ checker" + CR)
    print(CD + "  " + "-" * 40 + CR)
    print(CINFO + "  bamtech graphql api" + CR)
    print()


def usage():
    print("usage")
    print("  python " + os.path.basename(sys.argv[0]) + " <combo.txt> [proxy_file] [options]")
    print()
    print("options")
    print("  -t --threads n       workers default 20 max 2000")
    print("  -o --output dir      output dir default results")
    print("  --country code       filter results by country")
    print("  --resume             resume from progress json")
    print("  --otp-retry n        otp retries default 1 max 50")
    print("  --debug              verbose debug")
    print("  -h --help            this help")
    print()
    print("proxy formats")
    print("  host:port:user:pass")
    print("  user:pass:host:port")
    print("  user:pass@host:port")
    print("  http://user:pass@host:port")
    print("  socks5://user:pass@host:port")
    sys.exit(0)


def config(total, threads, pcount, cfilter, outdir, debug, resume, otp_retry=1):
    print("configuration")
    print("  " + "-" * 40)
    print("  combos    " + str(total))
    print("  threads   " + str(threads))
    print("  proxy     " + (str(pcount) + " loaded" if pcount else "direct"))
    print("  country   " + (cfilter if cfilter else "all"))
    print("  otp retry " + str(otp_retry))
    print("  output    " + outdir + "/")
    fl = []
    if debug: fl.append("debug")
    if resume: fl.append("resume")
    print("  flags     " + (", ".join(fl) if fl else "none"))
    print("  " + "-" * 40)
    print()


def summary(cnt, total, elapsed, outdir, pstats=None, cstats=None):
    cpm = total / max(elapsed, 1)
    print()
    print("summary")
    print("  " + "-" * 40)
    print("  valid    " + str(cnt["valid"]))
    print("  expired  " + str(cnt["expired"]))
    print("  otp      " + str(cnt["otp"]))
    print("  reset    " + str(cnt.get("reset", 0)))
    print("  invalid  " + str(cnt["invalid"]))
    print("  unknown  " + str(cnt["unknown"]))
    print("  error    " + str(cnt["error"]))
    print("  " + "-" * 40)
    print("  time " + str(round(elapsed, 1)) + "s  cpm " + str(round(cpm, 1)))
    if pstats:
        print("  proxy " + str(pstats["active"]) + "/" + str(pstats["total"]) + " active " + str(pstats["dead"]) + " dead")
    if cstats:
        print("  by country")
        for k, v in sorted(cstats.items(), key=lambda x: -x[1])[:15]:
            print("    " + k.ljust(3) + " " + str(v))
    print("  output " + outdir + "/")
    print()


def fline(r):
    if not r: return ""
    s = r.get("status", "")
    a = r.get("account", "")
    cc = r.get("country", "?")
    if s == "VALID":
        plan = r.get("plan", ""); exp = r.get("expires", ""); dl = r.get("days_left", "")
        ar = "auto" if r.get("auto_renew") else "manual"
        tr = " trial" if r.get("is_free_trial") else ""
        return "  [+] " + a + " | " + plan + tr + " | " + cc + " | exp " + str(exp) + " (" + str(dl) + "d) " + ar
    elif s == "EXPIRED":
        return "  [!] " + a + " | " + r.get("plan", "") + " | " + cc + " | exp " + str(r.get("expires", ""))
    elif s == "OTP":
        return "  [o] " + a + " | " + r.get("info", "") + " | " + cc
    elif s == "RESET":
        return "  [r] " + a + " | " + r.get("info", "") + " | " + cc
    elif s == "INVALID":
        return "  [-] " + a + " | " + r.get("info", "") + " | " + cc
    elif s == "UNKNOWN":
        return "  [?] " + a + " | " + r.get("info", "")
    return "  [x] " + a + " | " + r.get("info", "")
