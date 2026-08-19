FROM public.ecr.aws/lambda/python:3.14

COPY lambda/data_seeder/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/data_seeder ${LAMBDA_TASK_ROOT}

CMD ["data_seeder_lambda.handler"]