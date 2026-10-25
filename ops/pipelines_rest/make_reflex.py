import json, base64, sys, os
WS="ab773695-6bc2-4b52-8204-ea779d1c206c"; ES="d96ddbe5-80b6-45d8-8564-319dccde710e"; PL=sys.argv[2]
g=lambda n:"%08x-0000-4000-8000-%012x"%(0xa0000000+n,n)
C,SRC,EV,OBJ,ID,LR,OV,ACT,RULE=[g(i) for i in range(1,10)]
def inst(t,steps): return json.dumps({"templateId":t,"templateVersion":"1.1","steps":steps})
def arg(n,t,v): return {"name":n,"type":t,"value":v}
cont={"parentContainer":{"targetUniqueIdentifier":C}}
def attr(uid,name,field,typ):
    return {"uniqueIdentifier":uid,"type":"timeSeriesView-v1","payload":{"name":name,"parentObject":{"targetUniqueIdentifier":OBJ},**cont,"definition":{"type":"Attribute","instance":inst("BasicEventAttribute",[
      {"name":"EventSelectStep","id":g(100+int(uid[-2:],16)),"rows":[{"name":"EventSelector","kind":"Event","arguments":[{"kind":"EventReference","type":"complex","arguments":[arg("entityId","string",EV)],"name":"event"}]},{"name":"EventFieldSelector","kind":"EventField","arguments":[arg("fieldName","string",field)]}]},
      {"name":"EventComputeStep","id":g(200+int(uid[-2:],16)),"rows":[{"name":"TypeAssertion","kind":"TypeAssertion","arguments":[arg("op","string",typ),arg("format","string","")]}]}])}}}
ent=[
 {"uniqueIdentifier":C,"type":"container-v1","payload":{"name":"act_delivery_risk_alerts","type":"samples"}},
 {"uniqueIdentifier":SRC,"type":"eventstreamSource-v1","payload":{"name":"es_checkout_events","metadata":{"eventstreamArtifactId":ES},**cont}},
 {"uniqueIdentifier":EV,"type":"timeSeriesView-v1","payload":{"name":"Checkout events",**cont,"definition":{"type":"Event","instance":inst("SourceEvent",[{"name":"SourceEventStep","id":g(50),"rows":[{"name":"SourceSelector","kind":"SourceReference","arguments":[arg("entityId","string",SRC)]}]}])}}},
 {"uniqueIdentifier":OBJ,"type":"timeSeriesView-v1","payload":{"name":"Order",**cont,"definition":{"type":"Object"}}},
 {"uniqueIdentifier":ID,"type":"timeSeriesView-v1","payload":{"name":"order_id","parentObject":{"targetUniqueIdentifier":OBJ},**cont,"definition":{"type":"Attribute","instance":inst("IdentityPartAttribute",[{"name":"IdPartStep","id":g(51),"rows":[{"name":"TypeAssertion","kind":"TypeAssertion","arguments":[arg("op","string","Text"),arg("format","string","")]}]}])}}},
 attr(LR,"late_risk","late_risk","Number"),
 attr(OV,"order_value","order_value","Number"),
 {"uniqueIdentifier":ACT,"type":"fabricItemAction-v1","payload":{"name":"Run pl_log_alert","fabricItem":{"itemId":PL,"workspaceId":WS,"itemType":"Pipeline"},"jobType":"Pipeline",**cont}},
]
def aref(uid): return {"kind":"AttributeReference","type":"complex","arguments":[arg("entityId","string",uid)],"name":"attribute"}
ACTMODE=os.environ.get("ACTMODE","fabric")
rule_steps=[
 {"name":"ScalarSelectStep","id":g(60),"rows":[{"name":"AttributeSelector","kind":"Attribute","arguments":[aref(LR)]}]},
 {"name":"ScalarDetectStep","id":g(61),"rows":[{"name":"NumberBecomes","kind":"NumberBecomes","arguments":[arg("op","string","BecomesGreaterThanOrEqual"),arg("value","number",0.7)]},{"name":"OccurrenceOption","kind":"EachTime","arguments":[]}]},
 {"name":"DimensionalFilterStep","id":g(62),"rows":[{"name":"AttributeSelector","kind":"Attribute","arguments":[aref(OV)]},{"name":"NumberValueCondition","kind":"NumberValueCondition","arguments":[arg("op","string",os.environ.get("FOP","IsGreaterThanOrEqualTo")),arg("threshold","number",200.0)]}]},
 {"name":"ActStep","id":g(63),"rows":[{"name":"FabricItemBinding","kind":"FabricItem","arguments":[arg("fabricItemActionId","string",ACT),
    {"name":"parameters","type":"array","values":[
      {"type":"string","value":"order_id=@order_id"},{"type":"string","value":"late_risk=@late_risk"},{"type":"string","value":"order_value=@order_value"}]}]}]}]
if ACTMODE.startswith("fi"):
    v=ACTMODE
    kind="FabricItemInvocation"
    a0={"kind":"FabricItemReference","type":"complex","arguments":[arg("entityId","string",ACT)],"name":"fabricItem"} if v=="fi1" else arg("fabricItemActionId","string",ACT)
    plist=[{"type":"string","value":"order_id=@order_id"}] 
    params={"name":"parameters","type":"array","values":[]} 
    rule_steps[-1]={"name":"ActStep","id":g(63),"rows":[{"name":"FabricItemBinding","kind":kind,"arguments":[arg("fabricJobConnectionDocumentId","string",ACT),arg("workspaceId","string",WS),arg("itemId","string",PL),arg("jobType","string","Pipeline"),arg("itemType","string","Pipeline"),{"name":"additionalInformation","type":"array","values":[]}]+([params] if os.environ.get("WITHP") else [])}]}
if ACTMODE=="email":
    rule_steps[3]={"name":"ActStep","id":g(63),"rows":[{"name":"EmailBinding","kind":"EmailMessage","arguments":[arg("messageLocale","string",""),{"name":"sentTo","type":"array","values":[{"type":"string","value":"fabricuser1@lostspace003outlook.onmicrosoft.com"}]},{"name":"copyTo","type":"array","values":[]},{"name":"bCCTo","type":"array","values":[]},{"name":"subject","type":"array","values":[{"type":"string","value":"Brightcart: high-risk order"}]},{"name":"headline","type":"array","values":[{"type":"string","value":"High risk order"}]},{"name":"optionalMessage","type":"array","values":[{"type":"string","value":"check"}]},{"name":"additionalInformation","type":"array","values":[]}]}]}
if os.environ.get("NOFILTER"): rule_steps=[x for x in rule_steps if x["name"]!="DimensionalFilterStep"]
if os.environ.get("OP"): rule_steps[1]["rows"][0]["arguments"][0]["value"]=os.environ["OP"]
ent.append({"uniqueIdentifier":RULE,"type":"timeSeriesView-v1","payload":{"name":"High-risk high-value checkout","parentObject":{"targetUniqueIdentifier":OBJ},**cont,"definition":{"type":"Rule","instance":inst("AttributeTrigger",rule_steps),"settings":{"shouldRun":True,"shouldApplyRuleOnUpdate":False}}}})
STAGE=int(os.environ.get("STAGE","99"))
if STAGE<99: ent=[e for e in ent if e["uniqueIdentifier"] not in ([RULE,ACT,LR,OV] if STAGE==1 else [RULE,ACT] if STAGE==2 else [RULE] if STAGE==3 else [])]
b=base64.b64encode(json.dumps(ent).encode()).decode()
d={"definition":{"parts":[{"path":"ReflexEntities.json","payload":b,"payloadType":"InlineBase64"}]}}
json.dump(d,open(sys.argv[1]+".upd","w")); import os; d.update(displayName=os.environ.get("RNAME","act_delivery_risk_alerts"),type="Reflex"); json.dump(d,open(sys.argv[1],"w"))
