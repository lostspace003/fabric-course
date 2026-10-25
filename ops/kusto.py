"""Run a KQL / management command on a Fabric KQL database: python ops/kusto.py <queryServiceUri> <dbName> "<command>" """
import json, subprocess, sys, requests
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
uri, db, cmd = sys.argv[1:4]
tok = json.loads(subprocess.run(f"az account get-access-token --resource {uri} -o json", shell=True, capture_output=True, text=True).stdout)["accessToken"]
path = "/v1/rest/mgmt" if cmd.lstrip().startswith(".") else "/v1/rest/query"
r = requests.post(uri + path, headers={"Authorization": "Bearer " + tok}, json={"db": db, "csl": cmd})
if r.status_code != 200: print("HTTP", r.status_code, r.text[:600]); sys.exit(1)
t = r.json()["Tables"][0]; print([c["ColumnName"] for c in t["Columns"]]); [print(x) for x in t["Rows"][:12]]
