FROM public.ecr.aws/lambda/python:3.14

COPY lambda/ticketing/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/ticketing ${LAMBDA_TASK_ROOT}

CMD ["ticketing_lambda.handler"]