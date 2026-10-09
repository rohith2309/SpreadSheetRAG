from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated
import boto3
import os
from dotenv import load_dotenv
import json

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

lambda_client=boto3.client("lambda",region_name=AWS_REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


@tool
def RCEpythonTool(code:str, file_id : Annotated[str,InjectedState("file_id")], file_url: Annotated[str,InjectedState("file_url")]) -> dict: 
    """
    Executes pandas code inside a remote AWS Lambda worker against the user's Excel file.
    A pre-loaded DataFrame is accessible as 'df'.
    Always save the computed answer to a variable named 'result' or print() it.
    """
    
    if not file_id or not file_url:
        return {"status":"ERROR", "TYPE":"file_url or file_id is None"}
    
    
    payload={
        "file_id":file_id,
        "file_url":file_url,
        "code":code
    }
    
    
    response = lambda_client.invoke(
        FunctionName="PythonRCETool",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    result_payload = json.loads(response["Payload"].read().decode("utf-8"))
    
    return result_payload