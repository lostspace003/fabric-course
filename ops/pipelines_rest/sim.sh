#!/bin/bash
# usage: sim.sh N seed  -> sends events using the CURRENT eventstream connection string (fetched fresh; avoids stale .env)
cd "C:/Users/losts/Desktop/Course Factory/courses/FABRIC/fabric-course"
E=https://api.fabric.microsoft.com/v1/workspaces/ab773695-6bc2-4b52-8204-ea779d1c206c/eventstreams/d96ddbe5-80b6-45d8-8564-319dccde710e
SID=$(az rest --resource https://api.fabric.microsoft.com --method get --url $E/topology --query "sources[0].id" -o tsv)
az rest --resource https://api.fabric.microsoft.com --method get --url $E/sources/$SID/connection -o json | python -c "
import sys,json;d=json.load(sys.stdin);open('ops/pipelines_rest/_c.txt','w').write(d['eventHubName']+'\n'+d['accessKeys']['primaryConnectionString'])"
export EVENTSTREAM_ENTITY_NAME=$(sed -n 1p ops/pipelines_rest/_c.txt) EVENTSTREAM_CONNECTION_STRING=$(sed -n 2p ops/pipelines_rest/_c.txt); rm ops/pipelines_rest/_c.txt
.venv/Scripts/python.exe ops/simulate_live.py $1 $2 2>&1 | tail -2 | cut -c1-150
