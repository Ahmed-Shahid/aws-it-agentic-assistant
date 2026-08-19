@REM API STATE MACHINE
aws lambda invoke --function-name <ApiStateMachineFunctionName> --payload file://api_state_machine_event.json --cli-binary-format raw-in-base64-out out.json