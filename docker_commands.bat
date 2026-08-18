cd lambda\api_state_machine
docker build -t api_state_machine .

cd ..\intake_context
docker build -t intake_context .

cd ..\issue_resolution
docker build -t issue_resolution .

cd ..\ticketing
docker build -t ticketing .

cd ..\upload_document
docker build -t upload_document .

cd ..\..