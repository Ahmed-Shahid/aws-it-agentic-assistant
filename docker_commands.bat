cd lambda\api_state_machine
docker build -t api_state_machine .

cd ..\intake_context
docker build -t intake_context .

cd ..\issue_resolution
docker build -t issue_resolution .

cd ..\ticketing
docker build -t ticketing .

cd ..\..