FROM public.ecr.aws/lambda/python:3.14

COPY lambda/intake_context/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/intake_context ${LAMBDA_TASK_ROOT}

CMD ["intake_context_lambda.handler"]