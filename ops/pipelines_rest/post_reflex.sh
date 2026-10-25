cd "C:/Users/losts/Desktop/Course Factory/courses/FABRIC/fabric-course"
.venv/Scripts/python.exe ops/pipelines_rest/make_reflex.py ops/pipelines_rest/reflex_body.json 19172602-3a30-4608-b060-72947e81f4d2 || exit 1
az rest --resource https://api.fabric.microsoft.com --method post --url https://api.fabric.microsoft.com/v1/workspaces/ab773695-6bc2-4b52-8204-ea779d1c206c/reflexes --body @ops/pipelines_rest/reflex_body.json --verbose 2>&1 | grep -E "status|ERROR" | sed 's/\\*"//g' | cut -c1-3000
