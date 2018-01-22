import boto3
import os
import json
from uuid import uuid4 as Uuid
import decimal


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def state_table():
    return boto3.resource('dynamodb').Table(os.environ['STATE_TABLE_NAME'])


def get_temperature_sensor(uuid):
    temperature_sensor = state_table().get_item(Key={'uuid': uuid})
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(temperature_sensor['Item'], cls=DecimalEncoder)
    }
    return response


def get_all_temperature_sensors():
    temperature_sensors = state_table().scan()
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(temperature_sensors['Items'], cls=DecimalEncoder)
    }
    return response


def create_temperature_sensor(temperature_sensor_data):
    if ('area' not in temperature_sensor_data or
            not isinstance(temperature_sensor_data['area'], str)):
        raise Exception('Error. Must specify area.')
    if 'temperature_scale' not in temperature_sensor_data:
        temperature_sensor_data['temperature_scale'] = 'fahrenheit'
    elif (temperature_sensor_data['temperature_scale'] not in
            ['fahrenheit', 'celsius']):
        raise Exception(
            'Error. Temperature scale must be \'fahrenheit\' or \'celsius\'')
    uuid = Uuid().hex
    state = {
        'uuid': uuid,
        'area': temperature_sensor_data['area'],
        'temperature': 70,
        'temperature_scale': temperature_sensor_data['temperature_scale'],
        'update_period': 30
    }
    state_table().put_item(Item=state)
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'body': json.dumps(state)
    }
    return response


def update_temperature_sensor(uuid, temperature_sensor_data):
    updateExpressions = []
    attributeValues = {}
    if ('area' in temperature_sensor_data and
            isinstance(temperature_sensor_data['area'], str)):
        updateExpressions.append("area = :a")
        attributeValues[':a'] = temperature_sensor_data['area']
    if ('temperature' in temperature_sensor_data and
            isinstance(temperature_sensor_data['temperature'], int)):
        updateExpressions.append("temperature = :t")
        attributeValues[':t'] = temperature_sensor_data['temperature']
    if ('temperature_scale' in temperature_sensor_data and
            temperature_sensor_data['temperature_scale'] in
            ['fahrenheit', 'celsius']):
        updateExpressions.append("temperature_scale = :s")
        attributeValues[':s'] = temperature_sensor_data['temperature_scale']
    if ('update_period' in temperature_sensor_data and
            isinstance(temperature_sensor_data['update_period'], int)):
        updateExpressions.append("update_period = :u")
        attributeValues[':u'] = temperature_sensor_data['update_period']

    if len(updateExpressions) < 1:
        raise Exception('Error. Invalid update request.')
    updateExpressionStr = "set " + (",".join(updateExpressions))
    state_table().update_item(
        Key={'uuid': uuid},
        UpdateExpression=updateExpressionStr,
        ExpressionAttributeValues=attributeValues)

    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": "{\"message\": \"Temperature sensor updated\"}"
    }
    return response


def delete_temperature_sensor(uuid):
    # Delete tempearture sensor state
    state_table().delete_item(Key={'uuid': uuid})
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": "{\"message\": \"Temperature sensor deleted.\"}"
    }
    return response


def lambda_handler(event, context):
    try:
        if event['httpMethod'] == "GET":
            if event['pathParameters'] and 'uuid' in event['pathParameters']:
                return get_temperature_sensor(event['pathParameters']['uuid'])
            else:
                return get_all_temperature_sensors()
        elif event['httpMethod'] == "POST":
            if event['body'] and not event['pathParameters']:
                return create_temperature_sensor(json.loads(event['body']))
            else:
                raise Exception('Error. HTTP body required for \
                                POST to create temperature sensor.')
        elif event['httpMethod'] == "PUT":
            if (event['body'] and event['pathParameters'] and
                    'uuid' in event['pathParameters']):
                return update_temperature_sensor(
                    event['pathParameters']['uuid'],
                    json.loads(event['body']))
        elif event['httpMethod'] == "DELETE":
            if event['pathParameters'] and 'uuid' in event['pathParameters']:
                return delete_temperature_sensor(
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
