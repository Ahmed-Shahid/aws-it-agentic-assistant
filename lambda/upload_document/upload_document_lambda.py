from common.db import execute_query
from common.embeddings import embed
import uuid
import json


def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here
    document_id = str(uuid.uuid4())
    document_name = event.get('document_name', 'Untitled Document')
    document_content = event.get('document_content', '')
    chunk_size = event.get('chunk_size', 500)  # Default chunk size is 500 characters
    # Split the document content into chunks
    chunks = [document_content[i:i + chunk_size] for i in range(0, len(document_content), chunk_size)]
    sql = ""
    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        embedding = embed(chunk)
        sql += f"""
        INSERT INTO document_chunks (chunk_id, document_id, document_name, chunk_content, embedding)
        VALUES ('{chunk_id}', '{document_id}', '{document_name}', '{chunk}', '{embedding}');
        """
    result = execute_query(sql)
    return {
        'statusCode': 200,
        'body': 'Hello from Upload Document Lambda!',
        'result': result
    }