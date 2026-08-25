@REM DATA SEEDER
aws lambda invoke --function-name AwsItAgenticAssistantStac-DataSeederLambdaE9CA47BA-h04IHErleYjE --payload file://seed-event.json --cli-binary-format raw-in-base64-out out.json