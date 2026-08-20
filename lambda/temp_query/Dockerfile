FROM public.ecr.aws/lambda/python:3.14

COPY lambda/temp_query/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/temp_query ${LAMBDA_TASK_ROOT}

CMD ["temp_query_lambda.handler"]