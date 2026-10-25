"""Run PySpark cells on a Fabric lakehouse through the Livy API (dry-run helper).
   python ops/livy_run.py <workspaceId> <lakehouseId> <sessionId> <file.py|-c 'code'>   (prints statement output, exit 1 on error)
   python ops/livy_run.py <workspaceId> <lakehouseId> --new            (prints a new session id)"""
import json, subprocess, sys, time, requests
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
def tok(): return json.loads(subprocess.run("az account get-access-token --resource https://api.fabric.microsoft.com -o json", shell=True, capture_output=True, text=True).stdout)["accessToken"]
def base(w, l): return f"https://api.fabric.microsoft.com/v1/workspaces/{w}/lakehouses/{l}/livyapi/versions/2023-12-01"
def H(): return {"Authorization": "Bearer " + tok(), "Content-Type": "application/json"}
def new(w, l):
    r = requests.post(base(w, l) + "/sessions", headers=H(), json={"name": "dry", "kind": "pyspark"}); r.raise_for_status(); return r.json()["id"]
def wait_idle(w, l, s):
    for _ in range(90):
        st = requests.get(f"{base(w,l)}/sessions/{s}", headers=H()).json().get("state")
        if st == "idle": return
        if st in ("dead", "error", "killed"): raise SystemExit("session " + st)
        time.sleep(10)
def run(w, l, s, code, timeout=1500):
    wait_idle(w, l, s)
    r = requests.post(f"{base(w,l)}/sessions/{s}/statements", headers=H(), json={"code": code, "kind": "pyspark"}); r.raise_for_status(); sid = r.json()["id"]
    t = time.time()
    while time.time() - t < timeout:
        j = requests.get(f"{base(w,l)}/sessions/{s}/statements/{sid}", headers=H()).json()
        if j.get("state") in ("available", "error", "cancelled"):
            o = j.get("output") or {}
            if o.get("status") == "ok": print(o["data"].get("text/plain", "")); return 0
            print("ERROR", o.get("ename"), o.get("evalue")); print("\n".join(o.get("traceback", []))[-2500:]); return 1
        time.sleep(5)
    print("timeout"); return 2
if __name__ == "__main__":
    w, l = sys.argv[1:3]
    if sys.argv[3] == "--new": print(new(w, l)); sys.exit()
    s = sys.argv[3]; code = sys.argv[5] if sys.argv[4] == "-c" else open(sys.argv[4], encoding="utf-8").read()
    sys.exit(run(w, l, s, code))
