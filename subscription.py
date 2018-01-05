from state import *


def subscription_table():
    return boto3.resource('dynamodb').Table(
        os.environ['SUBSCRIPTION_TABLE_NAME'])


def get_subscription(sub_arn):
    sub = subscription_table().get_item(Key={'sub_arn': sub_arn})
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(sub['Item'], cls=DecimalEncoder)
    }
    return response


# Get all subs to the hvac
def get_all_subscriptions(hvac_id):
    subs = conditions_table().query(
        KeyConditionExpression=Key('hvac_id').eq(hvac_id))
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(subs['Items'], cls=DecimalEncoder)
    }
    return response


def create_subscription(sub_data, hvac_id):
    if not sub_data['protocol'] or not isinstance(sub_data['protocol']):
        raise Exception("Error. Must specify protocol")
    if not sub_data['endpoint'] or not isinstance(sub_data['endpoint']):
        raise Exception("Error. Must specify endpoint")

    topic_arn = state_table().get_item(Key={'uuid': hvac_id})['TopicArn']

    sub_arn = sns.subscribe(
        TopicArn=topic_arn,
        Protocol=sub_data['protocol'],
        Endpoint=sub_data['endpoint'])['SubscriptionArn']
    sub = {
        'sub_arn': sub_arn,
        'hvac_id': hvac_id,
        'topic_arn': topic_arn,
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


def delete_subscription(sub_arn):
    sns.unsubscribe(SubscriptionArn=sub_arn)
    subscription_table().delete_item(
        Key={'sub_arn': sub_arn})
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": "{\"message\": \"Unsubscribed.\"}"
    }
    return response


def lambda_handler(event, context):
    try:
        if (not event['pathParameters'] or
                'uuid' not in event['pathParameters']):
            raise Exception("Error. Must include id of hvac")
        else:
            if event['httpMethod'] == "GET":
                if 'sub_arn' in event['pathParameters']:
                    return get_subscription(event['pathParameters']['sub_arn'])
                else:
                    return get_all_subscriptions(
                        event['pathParameters']['uuid'])

            elif event['httpMethod'] == "POST":
                if event['body']:
                    return create_subscription(
                        json.loads(event['body']),
                        event['pathParameters']['uuid'])
                else:
                    raise Exception(
                        'Error. HTTP body required for POST to subscribe.')

            elif event['httpMethod'] == "DELETE":
                if 'sub_arn' in event['pathParameters']:
                    return delete_subscription(
                        event['pathParameters']['sub_arn'])
            else:
                raise Exception("Invalid HTTP method")
    except Exception as e:
        response = {
            "isBase64Encoded": "false",
            "statusCode": 400,
            "body": "{\"errorMessage\": \"" + e.args[0] + ".\"}"
        }
        return response
