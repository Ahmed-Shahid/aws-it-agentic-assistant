FROM public.ecr.aws/lambda/python:3.14

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . ${LAMBDA_TASK_ROOT}

CMD ["upload_document_lambda.handler"]