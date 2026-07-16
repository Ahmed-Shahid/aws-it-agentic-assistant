from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_secretsmanager as secretsmanager
)

LAMBDA_RUNTIME = _lambda.Runtime.PYTHON_3_14
LAMBDA_ASSSET = _lambda.Code.from_asset("lambda")

class AwsItAgenticAssistantStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SECRETS
        jira_secret = secretsmanager.Secret(
            self, "JiraSecret",
            secret_name="jira_token"
        )

        claude_secret = secretsmanager.Secret(
            self, "ClaudeSecret",
            secret_name="claude_api_key"
        )

        # LAMBDAS
        intake_context_lambda = _lambda.Function(
            self, "IntakeContextLambda",
            runtime=LAMBDA_RUNTIME,
            code=LAMBDA_ASSSET,
            handler="intake_context_lambda.handler",
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )

        ticketing_lambda = _lambda.Function(
            self, "TicketingLambda",
            runtime=LAMBDA_RUNTIME,
            code=LAMBDA_ASSSET,
            handler="ticketing_lambda.handler",
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn,
                "JIRA_TOKEN_SECRET_ARN": jira_secret.secret_arn
            }
        )

        issue_resolution_preapr_lambda = _lambda.Function(
            self, "IssueResolutionPreAprLambda",
            runtime=LAMBDA_RUNTIME,
            code=LAMBDA_ASSSET,
            handler="issue_resolution_preapr_lambda.handler",
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )

        issue_resolution_postapr_lambda = _lambda.Function(
            self, "IssueResolutionPostAprLambda",
            runtime=LAMBDA_RUNTIME,
            code=LAMBDA_ASSSET,
            handler="issue_resolution_postapr_lambda.handler",
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )
