import json, base64, sys
variant=sys.argv[1]; out=sys.argv[2]
CONN="a10a6dc1-a87e-4ac2-bd29-faef544e2a27"
SERVER="ckhibkzc4ywe3n7vl3fb7a4srq-bmlk63qmacgufccaune5sq6enq.database.fabric.microsoft.com,1433"; DB="sqldb_brightcart_ops-effff7aa-e469-40ea-b9d6-086d407aaf74"
SQLDB_ID="effff7aa-e469-40ea-b9d6-086d407aaf74"; WS2="6eaf160b-000c-428d-8840-a349d943c46c"
ls={"name":"sqldb_brightcart_ops","properties":{"type":"FabricSqlDatabase","typeProperties":{"artifactId":SQLDB_ID,"workspaceId":WS2,"endpoint":SERVER}}}
expr=lambda s:{"value":s,"type":"Expression"}
if variant=="script":
    act={"name":"InsertRiskAlert","type":"Script","dependsOn":[],
     "policy":{"timeout":"0.12:00:00","retry":0,"retryIntervalInSeconds":30,"secureOutput":False,"secureInput":False},
     "typeProperties":{"scripts":[{"type":"NonQuery","text":"INSERT INTO dbo.risk_alerts (order_id, late_risk, order_value) VALUES (CAST(@order_id AS INT), @late_risk, @order_value);",
       "parameters":[{"name":"order_id","type":"String","value":expr("@pipeline().parameters.order_id"),"direction":"Input"},
                     {"name":"late_risk","type":"Double","value":expr("@pipeline().parameters.late_risk"),"direction":"Input"},
                     {"name":"order_value","type":"Double","value":expr("@pipeline().parameters.order_value"),"direction":"Input"}]}],
      "scriptBlockExecutionTimeout":"02:00:00"},
     "externalReferences":{"connection":CONN}}
else:
    act={"name":"LogRiskAlertProc","type":"SqlServerStoredProcedure","dependsOn":[],
     "policy":{"timeout":"0.12:00:00","retry":0,"retryIntervalInSeconds":30,"secureOutput":False,"secureInput":False},
     "typeProperties":{"storedProcedureName":"dbo.usp_log_risk_alert","storedProcedureParameters":{
        "order_id":{"value":expr("@int(pipeline().parameters.order_id)"),"type":"Int32"},
        "late_risk":{"value":expr("@pipeline().parameters.late_risk"),"type":"Double"},
        "order_value":{"value":expr("@pipeline().parameters.order_value"),"type":"Double"}}},
     "externalReferences":{"connection":CONN}}
content={"properties":{"parameters":{"order_id":{"type":"string","defaultValue":"0"},"late_risk":{"type":"float","defaultValue":0},"order_value":{"type":"float","defaultValue":0}},"activities":[act]}}
json.dump({"displayName":"pl_log_alert","type":"DataPipeline","definition":{"parts":[{"path":"pipeline-content.json","payload":base64.b64encode(json.dumps(content).encode()).decode(),"payloadType":"InlineBase64"}]}},open(out,"w"))
json.dump({"definition":json.load(open(out))["definition"]},open(out+".upd","w"))
