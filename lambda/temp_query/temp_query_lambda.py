from common.db import execute_query
import json


def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here
    sql = event.get('sql', '')
    result = execute_query(sql)
    return {
        'statusCode': 200,
        'body': 'Hello from Temp Query Lambda!',
        'result': result
    }