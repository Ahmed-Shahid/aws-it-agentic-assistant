@REM DATA SEEDER
aws lambda invoke --function-name AwsItAgenticAssistantStack-TempQueryLambda01368E9B-1R5EVn8mwiDe --payload file://seed-event.json --cli-binary-format raw-in-base64-out out.json