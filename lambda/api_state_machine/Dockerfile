FROM public.ecr.aws/lambda/python:3.14

COPY lambda/api_state_machine/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/api_state_machine ${LAMBDA_TASK_ROOT}

CMD ["api_state_machine_lambda.handler"]