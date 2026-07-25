@REM cd lambda\api_state_machine
@REM docker build -t api_state_machine .

cd ..\intake_context
docker build -t intake_context .

cd ..\issue_resolution_postapr
docker build -t issue_resolution_postapr .

cd ..\issue_resolution_preapr
docker build -t issue_resolution_preapr .