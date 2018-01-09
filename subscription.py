from state import *


def subscription_table():
    return boto3.resource('dynamodb').Table(
        os.environ['SUBSCRIPTION_TABLE_NAME'])


def get_subscription(uuid):
    sub = subscription_table().get_item(Key={'uuid': uuid})
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(sub['Item'], cls=DecimalEncoder)
    }
    return response


# Get all subs to the hvac
def get_all_subscriptions():
    subs = subscription_table().scan()
    print(subs)
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(subs['Items'], cls=DecimalEncoder)
    }
    return response


def create_subscription(sub_data):
    if (not sub_data['protocol'] or sub_data['protocol'] not in
        ['http', 'https', 'email', 'email-sns',
            'sms', 'sqs', 'application', 'lambda']):
        raise Exception("Error. Must specify protocol")
    if not sub_data['endpoint'] or not isinstance(sub_data['endpoint'], str):
        raise Exception("Error. Must specify endpoint")

    sns().subscribe(
        TopicArn=os.environ['TOPIC_TOPIC_ARN'],
        Protocol=sub_data['protocol'],
        Endpoint=sub_data['endpoint'])
    uuid = Uuid().hex
    sub = {
        'uuid': uuid,
        'protocol': sub_data['protocol'],
        'endpoint': sub_data['endpoint']
    }
    subscription_table().put_item(Item=sub)

    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(sub)
    }
    return response


def delete_subscription(uuid):
    s = subscription_table().get_item(Key={'uuid': uuid})
    subs = sns().list_subscriptions_by_topic(TopicArn=os.environ['TOPIC_TOPIC_ARN'])['Subscriptions']
    for sub in subs:
        if sub['Protocol'] == s['protocol'] and sub['Endpoint'] == s['endpoint']:
            sns().unsubscribe(SubscriptionArn=sub['SubscriptionArn'])
            break
    subscription_table().delete_item(Key={'uuid': uuid})
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": "{\"message\": \"Unsubscribed.\"}"
    }
    return response


def lambda_handler(event, context):
    try:
        if event['httpMethod'] == "GET":
            if event['pathParameters'] and 'uuid' in event['pathParameters']:
                return get_subscription(event['pathParameters']['uuid'])
            else:
                return get_all_subscriptions()
        elif event['httpMethod'] == "POST":
            if event['body']:
                return create_subscription(json.loads(event['body']))
            else:
                raise Exception(
                    'Error. HTTP body required for POST to subscribe.')

        elif event['httpMethod'] == "DELETE":
            if 'uuid' in event['pathParameters']:
                return delete_subscription(
                    event['pathParameters']['uuid'])
        else:
            raise Exception("Invalid HTTP method")
    except Exception as e:
        response = {
            "isBase64Encoded": "false",
            "statusCode": 400,
            "body": "{\"errorMessage\": \"" + e.args[0] + ".\"}"
        }
        return response
