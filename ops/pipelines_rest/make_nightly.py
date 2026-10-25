import json, base64, sys
# usage: make_nightly.py <outBody> [dsType] [srcType] [srcConn]
WS="ab773695-6bc2-4b52-8204-ea779d1c206c"; LH="ce7c4b58-8b31-47c1-90a1-77958da4f02d"
CONN="a10a6dc1-a87e-4ac2-bd29-faef544e2a27"
NB={}  # filled from items
import subprocess
items=json.loads(subprocess.check_output(f"az rest --resource https://api.fabric.microsoft.com --method get --url https://api.fabric.microsoft.com/v1/workspaces/{WS}/notebooks",shell=True))["value"]
for i in items: NB[i["displayName"]]=i["id"]
dsType=sys.argv[2] if len(sys.argv)>2 else "AzureSqlTable"; srcType=sys.argv[3] if len(sys.argv)>3 else "AzureSqlSource"
conn=sys.argv[4] if len(sys.argv)>4 else CONN
pol={"timeout":"0.12:00:00","retry":0,"retryIntervalInSeconds":30,"secureOutput":False,"secureInput":False}
expr=lambda s:{"value":s,"type":"Expression"}
copy={"name":"CopyOpenOrders","type":"Copy","dependsOn":[],"policy":pol,"typeProperties":{
  "source":{"type":srcType,"partitionOption":"None","queryTimeout":"02:00:00","datasetSettings":{"type":dsType,"typeProperties":{"schema":"dbo","table":"open_orders","database":"sqldb_brightcart_ops-effff7aa-e469-40ea-b9d6-086d407aaf74"},"linkedService":{"name":"sqldb_brightcart_ops","properties":{"type":"FabricSqlDatabase","typeProperties":{"artifactId":"effff7aa-e469-40ea-b9d6-086d407aaf74","workspaceId":"6eaf160b-000c-428d-8840-a349d943c46c","endpoint":"ckhibkzc4ywe3n7vl3fb7a4srq-bmlk63qmacgufccaune5sq6enq.database.fabric.microsoft.com,1433","database":"sqldb_brightcart_ops-effff7aa-e469-40ea-b9d6-086d407aaf74"}}}}},
  "sink":{"type":"LakehouseTableSink","tableActionOption":"Overwrite","datasetSettings":{"type":"LakehouseTable","typeProperties":{"table":"bronze_open_orders"},"linkedService":{"name":"lh_brightcart","properties":{"type":"Lakehouse","typeProperties":{"artifactId":LH,"workspaceId":WS,"rootFolder":"Tables"}}}}},
  "enableStaging":False,"translator":{"type":"TabularTranslator","typeConversion":True,"typeConversionSettings":{"allowDataTruncation":True,"treatBooleanAsNumber":False}}}}
def nb(name,nbname,params,dep):
    return {"name":name,"type":"TridentNotebook","dependsOn":[{"activity":dep,"dependencyConditions":["Succeeded"]}],"policy":pol,
      "typeProperties":{"notebookId":NB[nbname],"workspaceId":WS,"parameters":params}}
a2=nb("BuildOpenOrderFeatures","nb_02_features",{"mode":{"value":"open_orders","type":"string"}},"CopyOpenOrders")
a3=nb("ScoreOpenOrders","nb_04_batch_score",{"model_version":{"value":expr("@pipeline().parameters.modelVersion"),"type":"int"}},"BuildOpenOrderFeatures")
content={"properties":{"parameters":{"modelVersion":{"type":"int","defaultValue":0}},"activities":[copy,a2,a3]}}
d={"definition":{"parts":[{"path":"pipeline-content.json","payload":base64.b64encode(json.dumps(content).encode()).decode(),"payloadType":"InlineBase64"}]}}
json.dump(d,open(sys.argv[1]+".upd","w"))
d["displayName"]="pl_nightly_delivery_promise"; d["type"]="DataPipeline"; json.dump(d,open(sys.argv[1],"w"))
