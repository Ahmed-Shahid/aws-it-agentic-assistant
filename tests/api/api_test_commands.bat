@REM API STATE MACHINE
aws lambda invoke --function-name AwsItAgenticAssistantStac-ApiStateMachineLambdaD06-gMBoJ5RiKp1C --payload file://api_state_machine_event.json --cli-binary-format raw-in-base64-out out.json

@REM DATA SEEDER
aws lambda invoke --function-name AwsItAgenticAssistantStac-DataSeederLambdaE9CA47BA-h04IHErleYjE --payload '{"query_type":"db_sql"}' out.json