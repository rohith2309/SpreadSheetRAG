from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated
import boto3
import os
from dotenv import load_dotenv
import json
import logging

logging.basicConfig(
    filename="codegen.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

lambda_client=boto3.client("lambda",region_name=AWS_REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


@tool
def RCEpythonTool(
    code: str,
    files: Annotated[dict, InjectedState("files")]
) -> dict:
    """
    Executes Python pandas code in AWS Lambda and returns stdout or error tracebacks.
    A dictionary `FILES` is pre-defined in the global environment mapping each filename to its local file path.
    Example:
        df = pd.read_excel(FILES['Project-Management-Sample-Data.xlsx'], sheet_name='Sheet1', skiprows=5)
        print(df.head())
    Always use print() to output results.
    """
    if not files:
        return {"status": "ERROR", "error": "No files found in session state."}

    logging.info(f"code generated:\n{code}")

    # Clean mapping of {filename: s3_presigned_url}
    file_urls = {
        fname: {
            "file_id": fdata["file_id"],
            "s3_url": fdata["s3_url"]
        }
        for fname, fdata in files.items()
    }

    payload = {
        "files": file_urls,
        "code": code  # Untouched! Line numbers in tracebacks will match 1:1
    }

    response = lambda_client.invoke(
        FunctionName="PythonRCETool",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    result = json.loads(response["Payload"].read().decode("utf-8"))
    logging.info(f"Lambda response:\n{json.dumps(result, indent=2, default=str)}")
    return result
