def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here
    return {
        'statusCode': 200,
        'body': 'Hello from Ticketing Lambda!'
    }