#!/usr/bin/env python3

import aws_cdk as cdk

from aws_it_agentic_assistant.aws_it_agentic_assistant_stack import AwsItAgenticAssistantStack


app = cdk.App()
AwsItAgenticAssistantStack(app, "AwsItAgenticAssistantStack")

app.synth()
