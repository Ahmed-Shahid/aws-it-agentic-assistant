from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    ArnFormat,
    aws_lambda as _lambda,
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
        status_table = dynamodb.Table(
            self, "StatusTable",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        '''
        DATABASE - Data Table
        '''
        vpc = ec2.Vpc(
            self,
            "AgentVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                # Holds the NAT Gateway; nothing else needs to live here.
                ec2.SubnetConfiguration(
                    name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                # langgraph_agent_fn and postapproval_fn: need NAT (internet)
                # for Anthropic/Bedrock/Secrets Manager, so PRIVATE_WITH_EGRESS.
                ec2.SubnetConfiguration(
                    name="PrivateWithEgress",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                # RDS instance + RDS Proxy: no internet access needed or
                # wanted, so a real PRIVATE_ISOLATED group has to exist.
                ec2.SubnetConfiguration(
                    name="PrivateIsolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

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

        db_lambda_sg = ec2.SecurityGroup(self, "AgentDbLambdaSg", vpc=vpc)
        db_instance.connections.allow_default_port_from(db_lambda_sg)

        '''
        LAMBDAS
        '''
        data_seeder_lambda = _lambda.DockerImageFunction(
            self, "DataSeederLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/data_seeder/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.minutes(5),
            environment={
                "DB_HOST": db_instance.instance_endpoint.hostname,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_lambda_sg]
        )

        temp_query_lambda = _lambda.DockerImageFunction(
            self, "TempQueryLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/temp_query/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            timeout=Duration.seconds(30),
            environment={
                "DB_HOST": db_instance.instance_endpoint.hostname,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_lambda_sg]
        )

        intake_context_lambda = _lambda.DockerImageFunction(
            self, "IntakeContextLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/intake_context/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_lambda_sg],
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn,
                "DB_HOST": db_instance.instance_endpoint.hostname,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn,
                "STATUS_TABLE_NAME": status_table.table_name
            }
        )

        upload_document_lambda = _lambda.DockerImageFunction(
            self, "UploadDocumentLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/upload_document/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(60),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_lambda_sg],
            environment={
                "DB_HOST": db_instance.instance_endpoint.hostname,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn,
                "STATUS_TABLE_NAME": status_table.table_name
            }
        )

        ticketing_lambda = _lambda.DockerImageFunction(
            self, "TicketingLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/ticketing/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(60),
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn,
                "JIRA_TOKEN_SECRET_ARN": jira_secret.secret_arn,
                "STATUS_TABLE_NAME": status_table.table_name
            }
        )

        issue_resolution_lambda = _lambda.DockerImageFunction(
            self, "IssueResolutionLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/issue_resolution/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(60),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_lambda_sg],
            environment={
                "CLAUDE_API_KEY_SECRET_ARN": claude_secret.secret_arn,
                "DB_HOST": db_instance.instance_endpoint.hostname,
                "DB_NAME": "agentdb",
                "DB_USER": "postgres",
                "DB_PASSWORD_SECRET_ARN": db_instance.secret.secret_arn,
                "STATUS_TABLE_NAME": status_table.table_name
            }
        )

        api_state_machine_lambda = _lambda.DockerImageFunction(
            self, "ApiStateMachineLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=".",
                file="lambda/api_state_machine/Dockerfile"
            ),
            architecture=_lambda.Architecture.ARM_64,
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                "STATUS_TABLE_NAME": status_table.table_name
            }
        )

        '''
        STEP FUNCTIONS: TASKS
        '''
        intake_context_task = tasks.LambdaInvoke(
            self, "IntakeContextTask",
            lambda_function=intake_context_lambda,
            payload=sfn.TaskInput.from_object({
                "raw_input.$": "$.raw_input",
                "user_id.$": "$.user_id",
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        #TODO: Remove hardcoded actions because they are now being returned from the lambdas?

        initialize_ticketing_task = tasks.LambdaInvoke(
            self, "InitializeTicketingTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "initialize",
                "job_id.$": "$.job_id",
                "user_id.$": "$.user_id",
                "classification.$": "$.classification",
                "raw_input.$": "$.raw_input",
                "retrieved_chunks.$": "$.retrieved_chunks",
            }),
            output_path="$.Payload"
        )

        upload_document_task = tasks.LambdaInvoke(
            self, "UploadDocumentTask",
            lambda_function=upload_document_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "upload",
                "input.$": "$"
            }),
            output_path="$.Payload"
        )

        issue_resolution_preapr_task = tasks.LambdaInvoke(
            self, "IssueResolutionPreApprovalTask",
            lambda_function=issue_resolution_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "propose", 
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        update_ticket_proposed_resolution_task = tasks.LambdaInvoke(
            self, "UpdateTicketProposedResolutionTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "update",
                "job_id.$": "$.job_id",
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
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload",
            task_timeout=sfn.Timeout.duration(Duration.days(7))
        )

        mark_approval_task = tasks.LambdaInvoke(
            self, "MarkApprovalTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "approve",
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        mark_rejection_task = tasks.LambdaInvoke(
            self, "MarkRejectionTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "reject",
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        issue_resolution_postapr_task = tasks.LambdaInvoke(
            self, "IssueResolutionPostApprovalTask",
            lambda_function=issue_resolution_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "apply", 
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        close_ticket_task = tasks.LambdaInvoke(
            self, "CloseTicketTask",
            lambda_function=ticketing_lambda,
            payload=sfn.TaskInput.from_object({
                "action": "resolve",
                "job_id.$": "$.job_id"
            }),
            output_path="$.Payload"
        )

        '''
        STEP FUNCTIONS: STATE MACHINE
        '''
        state_machine_name = "ITAgenticAssistantWorkflow"
        state_machine_arn = self.format_arn(
            service="states",
            resource="stateMachine",
            resource_name=state_machine_name,
            arn_format=ArnFormat.COLON_RESOURCE_NAME
        )

        approval_choice = sfn.Choice(self, "ApprovalChoice")
        approval_choice.when(
            sfn.Condition.string_equals("$.approval_status", "approved"), 
            mark_approval_task.next(issue_resolution_postapr_task).next(close_ticket_task)
        )
        approval_choice.when(
            sfn.Condition.string_equals("$.approval_status", "rejected"), 
            mark_rejection_task.next(close_ticket_task)
        )

        intake_choice = sfn.Choice(self, "IntakeChoice")
        intake_choice.when(
            sfn.Condition.string_equals("$.action", "upload"),
            upload_document_task
        )
        intake_choice.otherwise(
            initialize_ticketing_task
            .next(issue_resolution_preapr_task)
            .next(update_ticket_proposed_resolution_task)
            .next(request_approval_task)
            .next(approval_choice)
        )

        request_approval_task.add_catch(
            mark_rejection_task,
            errors=["States.Timeout"],
            result_path="$.error",
        )
        
        state_machine_definition = intake_context_task.next(intake_choice)
        state_machine = sfn.StateMachine(
            self, "ITAgenticAssistantWorkflow",
            state_machine_name=state_machine_name,
            definition_body=sfn.DefinitionBody.from_chainable(state_machine_definition),
            timeout=Duration.days(8) # Adding headroom on top of the 7-day task timeout for approval
        )

        '''
        GRANTS AND ADDITIONAL SETUP
        '''
        status_table.grant_read_write_data(intake_context_lambda)
        status_table.grant_read_write_data(upload_document_lambda)
        status_table.grant_read_write_data(issue_resolution_lambda)
        status_table.grant_read_write_data(ticketing_lambda)
        status_table.grant_read_write_data(api_state_machine_lambda)
        
        jira_secret.grant_read(ticketing_lambda)
        claude_secret.grant_read(intake_context_lambda)
        claude_secret.grant_read(issue_resolution_lambda)
        claude_secret.grant_read(ticketing_lambda) # TODO: May remove later if ticketing_lambda doesn't need to call Claude directly

        api_url = api_state_machine_lambda.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        CfnOutput(self, "ApiUrl", value=api_url.url)

        api_state_machine_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"]
            )
        )
        api_state_machine_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine_arn]
            )
        )
        api_state_machine_lambda.add_environment("STATE_MACHINE_ARN", state_machine_arn)
        ticketing_lambda.add_environment("APPROVAL_BASE_URL", api_url.url)

        db_instance.secret.grant_read(data_seeder_lambda)
        db_instance.secret.grant_read(intake_context_lambda)
        db_instance.secret.grant_read(upload_document_lambda)
        db_instance.secret.grant_read(issue_resolution_lambda)
        db_instance.secret.grant_read(temp_query_lambda)

        bedrock_embed_policy = iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"],
        )
        data_seeder_lambda.add_to_role_policy(bedrock_embed_policy)
        intake_context_lambda.add_to_role_policy(bedrock_embed_policy)
        upload_document_lambda.add_to_role_policy(bedrock_embed_policy)