import json, base64, sys
WS="ab773695-6bc2-4b52-8204-ea779d1c206c"; LH="ce7c4b58-8b31-47c1-90a1-77958da4f02d"; CONN="02e6d260-2c17-48f0-a261-e7a5990c8bd9"
content = {"properties":{
 "parameters":{
  "baseUrl":{"type":"string","defaultValue":"https://raw.githubusercontent.com/lostspace003/fabric-course/main/data/history"},
  "files":{"type":"array","defaultValue":["customers.csv","orders.csv","shipments.csv","daily_ops.csv","weather_daily.csv"]}},
 "activities":[{"name":"ForEachFile","type":"ForEach","dependsOn":[],
  "typeProperties":{"items":{"value":"@pipeline().parameters.files","type":"Expression"},"isSequential":False,"batchCount":5,
   "activities":[{"name":"CopyFile","type":"Copy","dependsOn":[],
    "policy":{"timeout":"0.12:00:00","retry":0,"retryIntervalInSeconds":30,"secureOutput":False,"secureInput":False},
    "typeProperties":{
     "source":{"type":"BinarySource","storeSettings":{"type":"HttpReadSettings","requestMethod":"GET"},"formatSettings":{"type":"BinaryReadSettings"},"datasetSettings":{"type":"Binary","typeProperties":{"location":{"type":"HttpServerLocation","relativeUrl":{"value":"@{replace(pipeline().parameters.baseUrl, 'https://raw.githubusercontent.com', '')}/@{item()}","type":"Expression"}}},"externalReferences":{"connection":CONN}}},
     "sink":{"type":"BinarySink","storeSettings":{"type":"LakehouseWriteSettings"},"datasetSettings":{"type":"Binary","typeProperties":{"location":{"type":"LakehouseLocation","folderPath":"bronze/history","fileName":{"value":"@item()","type":"Expression"}}},"linkedService":{"name":"lh_brightcart","properties":{"type":"Lakehouse","typeProperties":{"artifactId":LH,"workspaceId":WS,"rootFolder":"Files"}}}}},
     "enableStaging":False}}]}}]}}
body={"displayName":"pl_ingest_history","type":"DataPipeline","definition":{"parts":[{"path":"pipeline-content.json","payload":base64.b64encode(json.dumps(content).encode()).decode(),"payloadType":"InlineBase64"}]}}
json.dump(body,open(sys.argv[1],"w"))
