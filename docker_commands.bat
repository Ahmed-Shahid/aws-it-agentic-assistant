@REM cd lambda\api_state_machine
docker build -f lambda\api_state_machine\Dockerfile -t api_state_machine .

@REM cd ..\intake_context
docker build -f lambda\intake_context\Dockerfile -t intake_context .

@REM cd ..\issue_resolution
docker build -f lambda\issue_resolution\Dockerfile -t issue_resolution .

@REM cd ..\ticketing
docker build -f lambda\ticketing\Dockerfile -t ticketing .

@REM cd ..\upload_document
docker build -f lambda\upload_document\Dockerfile -t upload_document .

@REM cd ..\data_seeder
docker build -f lambda\data_seeder\Dockerfile -t data_seeder .

@REM cd ..\temp_query
docker build -f lambda\temp_query\Dockerfile -t temp_query .

@REM cd ..\..