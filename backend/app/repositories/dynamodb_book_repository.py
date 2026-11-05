import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError


class DynamoDBBookRepository:
    def __init__(self):
        region = os.getenv("AWS_REGION", "ap-southeast-2")
        table_name = os.getenv(
            "BOOKS_TABLE_NAME",
            "bookswap-books"
        )

        dynamodb = boto3.resource(
            "dynamodb",
            region_name=region
        )

        self.table = dynamodb.Table(table_name)

    def get_all(self):
        books = []
        scan_kwargs = {}

        while True:
            response = self.table.scan(**scan_kwargs)
            books.extend(response.get("Items", []))

            last_key = response.get("LastEvaluatedKey")

            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        return books

    def get_by_id(self, book_id: str):
        response = self.table.get_item(
            Key={"book_id": book_id}
        )

        return response.get("Item")

    def create(self, book):
        book_data = book.model_dump()

        book_data["book_id"] = str(uuid4())
        book_data["status"] = "AVAILABLE"

        self.table.put_item(
            Item=book_data,
            ConditionExpression=(
                "attribute_not_exists(book_id)"
            )
        )

        return book_data

    def update(self, book_id: str, book):
        update_data = book.model_dump(
            exclude_unset=True
        )

        if not update_data:
            return self.get_by_id(book_id)

        expression_names = {}
        expression_values = {}
        update_parts = []

        for index, (field, value) in enumerate(
            update_data.items()
        ):
            name_key = f"#field{index}"
            value_key = f":value{index}"

            expression_names[name_key] = field
            expression_values[value_key] = value

            update_parts.append(
                f"{name_key} = {value_key}"
            )

        try:
            response = self.table.update_item(
                Key={"book_id": book_id},
                UpdateExpression=(
                    "SET " + ", ".join(update_parts)
                ),
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression=(
                    "attribute_exists(book_id)"
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

    def delete(self, book_id: str):
        try:
            self.table.delete_item(
                Key={"book_id": book_id},
                ConditionExpression=(
                    "attribute_exists(book_id)"
                )
            )

            return True

        except ClientError as error:
            error_code = error.response[
                "Error"
            ]["Code"]

            if error_code == (
                "ConditionalCheckFailedException"
            ):
                return False

            raise