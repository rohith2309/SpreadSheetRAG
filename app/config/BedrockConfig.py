from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse 
import os

load_dotenv()

def get_bedrock_llm():
   return ChatBedrockConverse(
   region_name=os.getenv("AWS_REGION_NAME"),
   temperature=0,
   model="us.amazon.nova-pro-v1:0",
   aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
   aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
   )