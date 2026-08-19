FROM public.ecr.aws/lambda/python:3.14

COPY lambda/issue_resolution/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/issue_resolution ${LAMBDA_TASK_ROOT}

CMD ["issue_resolution_lambda.handler"]