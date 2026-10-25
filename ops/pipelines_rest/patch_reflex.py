import sys,json,base64,subprocess,os
W="ab773695-6bc2-4b52-8204-ea779d1c206c"; R="ac2c8d56-2ba2-4b05-b11e-b6e77eb5ec8d"
out=subprocess.run(f"az rest --resource https://api.fabric.microsoft.com --method post --url https://api.fabric.microsoft.com/v1/workspaces/{W}/reflexes/{R}/getDefinition",shell=True,capture_output=True,text=True).stdout
d=json.loads(out); parts={p["path"]:p for p in d["definition"]["parts"]}
e=json.loads(base64.b64decode(parts["ReflexEntities.json"]["payload"]).decode().lstrip("\ufeff"))
mode=sys.argv[1]
by=lambda n:[x for x in e if x["payload"].get("name")==n]
streams=by("es_checkout_events-stream"); stream=streams[-1]["uniqueIdentifier"]
ID="a0000005-0000-4000-8000-000000000005"; LR="a0000006-0000-4000-8000-000000000006"; OV="a0000007-0000-4000-8000-000000000007"; EVOLD="a0000003-0000-4000-8000-000000000003"
SPLIT="a0000010-0000-4000-8000-000000000010"; OBJ="a0000004-0000-4000-8000-000000000004"; C="a0000001-0000-4000-8000-000000000001"
e=[x for x in e if x["uniqueIdentifier"]!=SPLIT]
split_inst=json.loads(os.environ["SPLIT"]) if os.environ.get("SPLIT") else None
if split_inst:
    split_inst=json.dumps(split_inst).replace("__STREAM__",stream).replace("__ID__",ID)
    e.append({"uniqueIdentifier":SPLIT,"type":"timeSeriesView-v1","payload":{"name":"Order events","parentContainer":{"targetUniqueIdentifier":C},"definition":{"type":"Event","instance":split_inst}}})
    ref=SPLIT
else: ref=stream
for x in e:
    if x["payload"].get("name") in ("late_risk","order_value"):
        x["payload"]["definition"]["instance"]=x["payload"]["definition"]["instance"].replace(EVOLD,ref)
parts["ReflexEntities.json"]["payload"]=base64.b64encode(json.dumps(e).encode()).decode()
json.dump({"definition":{"parts":[{"path":"ReflexEntities.json","payload":parts["ReflexEntities.json"]["payload"],"payloadType":"InlineBase64"}]}},open("ops/pipelines_rest/_reflex_patch.json","w"))
print("stream",stream)
