#!/bin/bash
# usage: runpl.sh <pipelineName> [bodyfile]  -> runs and waits, prints status + failure
W=ab773695-6bc2-4b52-8204-ea779d1c206c
P=$(az rest --resource https://api.fabric.microsoft.com --method get --url https://api.fabric.microsoft.com/v1/workspaces/$W/dataPipelines --query "value[?displayName=='$1'].id|[0]" -o tsv)
B=${2:-}
if [ -n "$B" ]; then A="--body @$B"; else A="--body {}"; fi
L=$(az rest --resource https://api.fabric.microsoft.com --method post --url "https://api.fabric.microsoft.com/v1/workspaces/$W/items/$P/jobs/instances?jobType=Pipeline" $A --verbose 2>&1 | grep -i "'Location'" | sed "s/.*: '//;s/'//")
/tmp/wait.sh $L | python -c "import sys,json;d=json.load(sys.stdin);print(d['status'],json.dumps(d.get('failureReason')))"
echo "run-url $L"
