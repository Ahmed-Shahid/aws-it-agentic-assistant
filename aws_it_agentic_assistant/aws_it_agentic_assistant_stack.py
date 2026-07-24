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
        intake_context_task = tasks.LambdaInvoke(
            self, "IntakeContextTask",
            lambda_function=intake_context_lambda,
            output_path="$.Payload"
        )

        initialize_ticketing_task = tasks.LambdaInvoke(
            self, "InitializeTicketingTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "initialize",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        issue_resolution_preapr_task = tasks.LambdaInvoke(
            self, "IssueResolutionPreApprovalTask",
            lambda_function=issue_resolution_preapr_lambda,
            output_path="$.Payload"
        )

        update_ticket_proposed_resolution_task = tasks.LambdaInvoke(
            self, "UpdateTicketProposedResolutionTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "update_proposed_resolution",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        request_approval_task = tasks.LambdaInvoke(
            self, "RequestApprovalTask",
            lambda_function=ticketing_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object({
                "action": "request_approval",
                "token": sfn.JsonPath.task_token,
                "input.$": "$"
            }),
            output_path="$.Payload",
            task_timeout=sfn.Timeout.duration(Duration.days(7))
        )

        mark_approval_task = tasks.LambdaInvoke(
            self, "MarkApprovalTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "approve",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        mark_rejection_task = tasks.LambdaInvoke(
            self, "MarkRejectionTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "reject",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        issue_resolution_postapr_task = tasks.LambdaInvoke(
            self, "IssueResolutionPostApprovalTask",
            lambda_function=issue_resolution_postapr_lambda,
            output_path="$.Payload"
        )

        close_ticket_task = tasks.LambdaInvoke(
            self, "CloseTicketTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "close",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        '''
        STEP FUNCTIONS: STATE MACHINE
        '''
        approval_choice = sfn.Choice(self, "ApprovalChoice")
        approval_choice.when(
            sfn.Condition.string_equals("$.approval_status", "approved"), 
            mark_approval_task.next(issue_resolution_postapr_task).next(close_ticket_task)
        )
        approval_choice.when(
            sfn.Condition.string_equals("$.approval_status", "rejected"), 
            mark_rejection_task.next(close_ticket_task)
        )
        state_machine_definition = (
            intake_context_task
            .next(initialize_ticketing_task)
            .next(issue_resolution_preapr_task)
            .next(update_ticket_proposed_resolution_task)
            .next(request_approval_task)
            .next(approval_choice)
        )
        state_machine = sfn.StateMachine(
            self, "ITAgenticAssistantWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(state_machine_definition),
            timeout=Duration.days(7)
        )

        '''
        GRANTS AND ADDITIONAL SETUP
        '''
        #TODO: Add status table grants
        jira_secret.grant_read(ticketing_lambda)
        claude_secret.grant_read(intake_context_lambda)

        api_url = api_state_machine_lambda.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.AWS_IAM,
        )

        CfnOutput(self, "ApiUrl", value=api_url.url)

        api_state_machine_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"]
            )
        )
        state_machine.grant_start_execution(api_state_machine_lambda)
        api_state_machine_lambda.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)