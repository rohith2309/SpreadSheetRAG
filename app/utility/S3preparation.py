import boto3
import pandas as pd

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['REGION_NAME']
)

def prepare_excel_for_rag(file_path: str, bucket: str, object_key: str):
    # 1. Upload to S3
    s3_client.upload_file(file_path, bucket, object_key)
    
    # 2. Generate a Presigned URL (valid for 1 hour)
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': object_key},
        ExpiresIn=3600
    )
    
    # 3. Extract lightweight metadata for the LLM
    # We only read 5 rows locally to save memory on the app server
    df_preview = pd.read_excel(file_path, nrows=5)
    
    metadata = {
        "columns": list(df_preview.columns),
        "dtypes": df_preview.dtypes.astype(str).to_dict(),
        "sample_data": df_preview.head(2).to_dict(orient="records")
    }
    
    return presigned_url, metadata