import os
from datetime import datetime, timezone
from uuid import uuid4
from boto3.dynamodb.types import TypeSerializer

import boto3
from botocore.exceptions import ClientError


class DynamoDBExchangeRepository:
    def __init__(self):
        region = os.getenv("AWS_REGION", "ap-southeast-2")
        table_name = os.getenv(
            "EXCHANGE_REQUESTS_TABLE_NAME",
            "bookswap-exchange-requests"
        )

        dynamodb = boto3.resource(
            "dynamodb",
            region_name=region
        )

        self.table = dynamodb.Table(table_name)
        self.client = boto3.client(
            "dynamodb",
            region_name=region
        )
        self.serializer = TypeSerializer()

        self.books_table_name = os.getenv(
            "BOOKS_TABLE_NAME",
            "bookswap-books"
        )

    def get_all(self):
        requests = []
        scan_kwargs = {}

        while True:
            response = self.table.scan(**scan_kwargs)
            requests.extend(response.get("Items", []))

            last_key = response.get("LastEvaluatedKey")

            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        return sorted(
            requests,
            key=lambda item: item.get("created_at", ""),
            reverse=True
        )

    def get_by_id(self, request_id: str):
        response = self.table.get_item(
            Key={"request_id": request_id}
        )

        return response.get("Item")

    def create(
        self,
        requested_book_id: str,
        requester_name: str,
        message: str = ""
    ):
        request_data = {
            "request_id": str(uuid4()),
            "requested_book_id": requested_book_id,
            "requester_name": requester_name,
            "message": message,
            "status": "PENDING",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        self.table.put_item(
            Item=request_data,
            ConditionExpression=(
                "attribute_not_exists(request_id)"
            )
        )

        return request_data

    def update_status(
        self,
        request_id: str,
        status: str
    ):
        try:
            response = self.table.update_item(
                Key={"request_id": request_id},
                UpdateExpression=(
                    "SET #status = :status, "
                    "#updated_at = :updated_at"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#updated_at": "updated_at"
                },
                ExpressionAttributeValues={
                    ":status": status,
                    ":updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    ":pending": "PENDING"
                },
                ConditionExpression=(
                    "attribute_exists(request_id) "
                    "AND #status = :pending"
                ),
                ReturnValues="ALL_NEW"
            )

            return response.get("Attributes")

        except ClientError as error:
            error_code = error.response[
                "Error"
            ]["Code"]

            if error_code == (
                "ConditionalCheckFailedException"
            ):
                return None

            raise
    def accept_request(self, request_id: str, book_id: str):
        now = datetime.now(timezone.utc).isoformat()

        def serialize(values):
            return {
                key: self.serializer.serialize(value)
                for key, value in values.items()
            }

        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": serialize({
                                "request_id": request_id
                            }),
                            "UpdateExpression": (
                                "SET #status = :accepted, "
                                "#updated_at = :now"
                            ),
                            "ConditionExpression": (
                                "attribute_exists(request_id) "
                                "AND #status = :pending "
                                "AND requested_book_id = :book_id"
                            ),
                            "ExpressionAttributeNames": {
                                "#status": "status",
                                "#updated_at": "updated_at"
                            },
                            "ExpressionAttributeValues": serialize({
                                ":accepted": "ACCEPTED",
                                ":pending": "PENDING",
                                ":book_id": book_id,
                                ":now": now
                            })
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.books_table_name,
                            "Key": serialize({
                                "book_id": book_id
                            }),
                            "UpdateExpression": (
                                "SET #status = :reserved"
                            ),
                            "ConditionExpression": (
                                "attribute_exists(book_id) "
                                "AND #status = :available"
                            ),
                            "ExpressionAttributeNames": {
                                "#status": "status"
                            },
                            "ExpressionAttributeValues": serialize({
                                ":reserved": "RESERVED",
                                ":available": "AVAILABLE"
                            })
                        }
                    }
                ]
            )

            return self.get_by_id(request_id)

        except ClientError as error:
            error_code = error.response["Error"]["Code"]

            if error_code == "TransactionCanceledException":
                reasons = error.response.get(
                    "CancellationReasons", []
                )

                if reasons and all(
                    reason.get("Code") in (
                        "None",
                        "ConditionalCheckFailed"
                    )
                    for reason in reasons
                ):
                    return None

            raise