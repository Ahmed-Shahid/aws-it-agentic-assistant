cdk init sample-app --language python

@REM Set up Code

aws configure set ca_bundle /path/to/your/certificate.pem
@REM set AWS_CA_BUNDLE=/path/to/your/certificate.pem
aws login 
cdk bootstrap --ca-bundle-path /path/to/your/certificate.pem
cdk synth
cdk destroy