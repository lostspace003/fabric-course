"""List OneLake DFS path: python ops/onelake_ls.py <wsId> <itemId> <path>"""
import sys, json, subprocess, urllib.request
tok=json.loads(subprocess.check_output("az account get-access-token --resource https://storage.azure.com/ -o json",shell=True))["accessToken"]
ws,item,path=sys.argv[1:4]
u=f"https://onelake.dfs.fabric.microsoft.com/{ws}?resource=filesystem&recursive=false&directory={item}/{path}"
r=urllib.request.urlopen(urllib.request.Request(u,headers={"Authorization":"Bearer "+tok}))
for p in json.load(r).get("paths",[]): print(p["name"].split("/")[-1], p.get("contentLength"), p["lastModified"])
