from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_secretsmanager as secretsmanager,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
)

class AwsItAgenticAssistantStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''
        SECRETS
        '''
        jira_secret = secretsmanager.Secret(
            self, "JiraSecret",
            secret_name="jira_token"
        )

        claude_secret = secretsmanager.Secret(
            self, "ClaudeSecret",
            secret_name="claude_api_key"
        )

        '''
        DATABASE
        '''
        #TODO: Implement Postgres Status Table

        '''
        LAMBDAS
        '''
        intake_context_lambda = _lambda.DockerImageFunction(
            self, "IntakeContextLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/intake_context"
            ),
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )

        ticketing_lambda = _lambda.DockerImageFunction(
            self, "TicketingLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/ticketing"
            ),
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn,
                "JIRA_TOKEN_SECRET_ARN": jira_secret.secret_arn
            }
        )

        issue_resolution_preapr_lambda = _lambda.DockerImageFunction(
            self, "IssueResolutionPreAprLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/issue_resolution_preapr"
            ),
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )

        issue_resolution_postapr_lambda = _lambda.DockerImageFunction(
            self, "IssueResolutionPostAprLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/issue_resolution_postapr"
            ),
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn
            }
        )

        api_state_machine_lambda = _lambda.DockerImageFunction(
            self, "ApiStateMachineLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/api_state_machine"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=256,
            timeout=Duration.seconds(30),
        )

        '''
        STEP FUNCTIONS: TASKS
        '''
        intake_context_task = None
        initialize_ticketing_task = None
        issue_resolution_preapr_task = None
        update_ticket_proposed_resolution_task = None
        request_approval_task = None
        mark_approval_task = None
        mark_rejection_task = None
        issue_resolution_postapr_task = None
        close_ticket_task = None

        '''
        STEP FUNCTIONS: STATE MACHINE
        '''

        '''
        GRANTS AND ADDITIONAL SETUP
        '''