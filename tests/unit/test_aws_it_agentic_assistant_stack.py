import aws_cdk as core
import aws_cdk.assertions as assertions
from aws_it_agentic_assistant.aws_it_agentic_assistant_stack import AwsItAgenticAssistantStack


def test_sqs_queue_created():
    app = core.App()
    stack = AwsItAgenticAssistantStack(app, "aws-it-agentic-assistant")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::SQS::Queue", {
        "VisibilityTimeout": 300
    })


def test_sns_topic_created():
    app = core.App()
    stack = AwsItAgenticAssistantStack(app, "aws-it-agentic-assistant")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::SNS::Topic", 1)
