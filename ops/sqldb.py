"""SQL helper for the Fabric SQL database (Entra token via az). python ops/sqldb.py <file.sql | -q "SELECT ...">  [server] [db]"""
import sys, struct, subprocess, json, re, pyodbc
SERVER = "ckhibkzc4ywe3n7vl3fb7a4srq-bmlk63qmacgufccaune5sq6enq.database.fabric.microsoft.com,1433"
DB = "sqldb_brightcart_ops-effff7aa-e469-40ea-b9d6-086d407aaf74"
def connect(server=SERVER, db=DB):
    tok = json.loads(subprocess.check_output("az account get-access-token --resource https://database.windows.net/ -o json", shell=True))["accessToken"].encode("utf-16-le")
    s = struct.pack(f"<I{len(tok)}s", len(tok), tok)
    return pyodbc.connect(f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};Encrypt=yes", attrs_before={1256: s}, autocommit=True)
def run_script(cn, text):
    cur = cn.cursor()
    for batch in re.split(r"^\s*GO\s*$", text, flags=re.M | re.I):
        if batch.strip(): cur.execute(batch)
if __name__ == "__main__":
    cn = connect()
    if sys.argv[1] == "-q":
        cur = cn.cursor(); cur.execute(sys.argv[2])
        if cur.description:
            print([d[0] for d in cur.description])
            for r in cur.fetchall(): print(tuple(r))
    else:
        run_script(cn, open(sys.argv[1], encoding="utf-8").read()); print("ok")
