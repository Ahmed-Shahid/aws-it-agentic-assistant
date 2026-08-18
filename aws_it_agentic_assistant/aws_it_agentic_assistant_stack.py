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
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_rds as rds,
    RemovalPolicy
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
        DATABASE - Status Table
        '''
        #TODO: Implement Postgres Status Table
        status_table = dynamodb.Table(
            self, "StatusTable",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        '''
        DATABASE - Data Table
        '''
        vpc = ec2.Vpc(self, "AgentVpc", max_azs=2, nat_gateways=1)

        db_instance = rds.DatabaseInstance(
            self,
            "AgentDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            database_name="agentdb",
            credentials=rds.Credentials.from_generated_secret("postgres"),
            # removal_policy=RemovalPolicy.DESTROY,  # convenient for POC teardown
        )

        db_proxy = rds.DatabaseProxy(
            self,
            "AgentDatabaseProxy",
            proxy_target=rds.ProxyTarget.from_instance(db_instance),
            secrets=[db_instance.secret],
            vpc=vpc,
        )

        db_lambda_sg = ec2.SecurityGroup(self, "AgentDbLambdaSg", vpc=vpc)
        db_proxy.connections.allow_default_port_from(db_lambda_sg)

        '''
        LAMBDAS
        '''
        data_seeder_lambda = _lambda.DockerImageFunction(
            self, "DataSeederLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/data_seeder"
            ),
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "DB_PROXY_ENDPOINT": db_proxy.endpoint,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn
            },
            vpc=vpc,
            security_groups=[db_lambda_sg]
        )

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

        #TODO: Consolidate the issue resolution lambdas into a single lambda with a mode parameter

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
        seed_data_task = tasks.LambdaInvoke(
            self, "SeedDataTask",
            lambda_function=data_seeder_lambda,
            output_path="$.Payload"
        )

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
            seed_data_task
            .next(intake_context_task)
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