FROM public.ecr.aws/lambda/python:3.14

COPY lambda/upload_document/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY common/ ${LAMBDA_TASK_ROOT}/common
COPY lambda/upload_document ${LAMBDA_TASK_ROOT}

CMD ["upload_document_lambda.handler"]