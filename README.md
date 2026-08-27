
# Welcome to AWS IT Agentic Assistant

## Running the Fully Integrated UI
```
cd streamlit_app
run.bat
```
NOTE: The app will only work with a valid `aws login` where the lambdas are deployed.

## Deploy AWS stack
Prerequisites:
- Make sure Docker Desktop is installed
- Make sure `docker build` has run for each lambda
```
aws configure set region us-west-2
cdk bootstrap
cdk deploy
```
NOTE: us-west-2 is required in order to utilize the AWS Bedrock Titan V2 Embedding model

## Test API
Example for testing api_state_machine lambda:
```
cd tests\lambda\api_state_machine
test_api_state_machine.bat
```
NOTES:
- Make sure you have run `aws login` and items are deployed
- Make sure the lambda function name and payload.json names are updated in the bat file
- Make sure the data in the json payloads are updated