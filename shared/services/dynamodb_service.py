"""
DynamoDB service for AI Pipeline Orchestrator v2.

Provides centralized DynamoDB operations with proper error handling and logging.
"""

import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal
from loguru import logger
import json


class DynamoDBService:
    """Service for DynamoDB operations."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize DynamoDB service.
        
        Args:
            region_name: AWS region name
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.region_name = region_name
    
    def get_table(self, table_name: str):
        """
        Get DynamoDB table resource.
        
        Args:
            table_name: Name of the DynamoDB table
            
        Returns:
            DynamoDB table resource
        """
        return self.dynamodb.Table(table_name)
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """
        Put item into DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            item: Item data to store
            
        Returns:
            True if successful
            
        Raises:
            ClientError: If put operation fails
        """
        try:
            table = self.get_table(table_name)
            
            # Convert any float values to Decimal for DynamoDB compatibility
            processed_item = self._convert_floats_to_decimals(item)
            
            table.put_item(Item=processed_item)
            
            logger.info(
                "DynamoDB item stored",
                table=table_name,
                item_keys=list(item.keys())
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to put DynamoDB item",
                table=table_name,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get item from DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            key: Primary key dictionary
            
        Returns:
            Item data or None if not found
        """
        try:
            table = self.get_table(table_name)
            
            response = table.get_item(Key=key)
            
            item = response.get('Item')
            if item:
                # Convert Decimal back to float for JSON serialization
                item = self._convert_decimals_to_floats(item)
                
                logger.info(
                    "DynamoDB item retrieved",
                    table=table_name,
                    key=key,
                    found=True
                )
            else:
                logger.info(
                    "DynamoDB item not found",
                    table=table_name,
                    key=key,
                    found=False
                )
            
            return item
            
        except ClientError as e:
            logger.error(
                "Failed to get DynamoDB item",
                table=table_name,
                key=key,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def query_items(self, table_name: str, key_condition_expression: str, 
                   expression_attribute_values: Dict[str, Any], 
                   index_name: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query items from DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            key_condition_expression: Key condition expression
            expression_attribute_values: Expression attribute values
            index_name: Optional GSI name
            limit: Optional limit on results
            
        Returns:
            List of items
        """
        try:
            table = self.get_table(table_name)
            
            query_args = {
                'KeyConditionExpression': key_condition_expression,
                'ExpressionAttributeValues': self._convert_floats_to_decimals(expression_attribute_values)
            }
            
            if index_name:
                query_args['IndexName'] = index_name
            
            if limit:
                query_args['Limit'] = limit
            
            response = table.query(**query_args)
            
            items = response.get('Items', [])
            items = [self._convert_decimals_to_floats(item) for item in items]
            
            logger.info(
                "DynamoDB items queried",
                table=table_name,
                index=index_name,
                item_count=len(items)
            )
            
            return items
            
        except ClientError as e:
            logger.error(
                "Failed to query DynamoDB items",
                table=table_name,
                index=index_name,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def scan_items(self, table_name: str, filter_expression: Optional[str] = None,
                  expression_attribute_values: Optional[Dict[str, Any]] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scan items from DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            filter_expression: Optional filter expression
            expression_attribute_values: Optional expression attribute values
            limit: Optional limit on results
            
        Returns:
            List of items
        """
        try:
            table = self.get_table(table_name)
            
            scan_args = {}
            
            if filter_expression:
                scan_args['FilterExpression'] = filter_expression
                
            if expression_attribute_values:
                scan_args['ExpressionAttributeValues'] = self._convert_floats_to_decimals(expression_attribute_values)
                
            if limit:
                scan_args['Limit'] = limit
            
            response = table.scan(**scan_args)
            
            items = response.get('Items', [])
            items = [self._convert_decimals_to_floats(item) for item in items]
            
            logger.info(
                "DynamoDB items scanned",
                table=table_name,
                item_count=len(items)
            )
            
            return items
            
        except ClientError as e:
            logger.error(
                "Failed to scan DynamoDB items",
                table=table_name,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def update_item(self, table_name: str, key: Dict[str, Any], 
                   update_expression: str, expression_attribute_values: Dict[str, Any],
                   expression_attribute_names: Optional[Dict[str, str]] = None) -> bool:
        """
        Update item in DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            key: Primary key dictionary
            update_expression: Update expression
            expression_attribute_values: Expression attribute values
            expression_attribute_names: Optional expression attribute names
            
        Returns:
            True if successful
        """
        try:
            table = self.get_table(table_name)
            
            update_args = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': self._convert_floats_to_decimals(expression_attribute_values)
            }
            
            if expression_attribute_names:
                update_args['ExpressionAttributeNames'] = expression_attribute_names
            
            table.update_item(**update_args)
            
            logger.info(
                "DynamoDB item updated",
                table=table_name,
                key=key
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to update DynamoDB item",
                table=table_name,
                key=key,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """
        Delete item from DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            key: Primary key dictionary
            
        Returns:
            True if successful
        """
        try:
            table = self.get_table(table_name)
            
            table.delete_item(Key=key)
            
            logger.info(
                "DynamoDB item deleted",
                table=table_name,
                key=key
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to delete DynamoDB item",
                table=table_name,
                key=key,
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise
    
    def _convert_floats_to_decimals(self, obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB compatibility.
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with floats converted to Decimals
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {key: self._convert_floats_to_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimals(item) for item in obj]
        else:
            return obj
    
    def _convert_decimals_to_floats(self, obj: Any) -> Any:
        """
        Recursively convert Decimal values to float for JSON serialization.
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with Decimals converted to floats
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals_to_floats(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_floats(item) for item in obj]
        else:
            return obj
    
    def batch_write_items(self, table_name: str, items: List[Dict[str, Any]], 
                         operation: str = 'put') -> bool:
        """
        Batch write items to DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            items: List of items to write
            operation: 'put' or 'delete'
            
        Returns:
            True if successful
        """
        try:
            table = self.get_table(table_name)
            
            # DynamoDB batch_writer handles batching automatically
            with table.batch_writer() as batch:
                for item in items:
                    if operation == 'put':
                        processed_item = self._convert_floats_to_decimals(item)
                        batch.put_item(Item=processed_item)
                    elif operation == 'delete':
                        batch.delete_item(Key=item)
            
            logger.info(
                "DynamoDB batch write completed",
                table=table_name,
                item_count=len(items),
                operation=operation
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to batch write DynamoDB items",
                table=table_name,
                operation=operation,
                item_count=len(items),
                error_code=e.response['Error']['Code'],
                error_message=str(e)
            )
            raise