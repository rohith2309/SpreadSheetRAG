from fastapi import FastAPI,File, UploadFile, HTTPException
import boto3
import os
from dotenv import load_dotenv
from schemas.CreateSessionResponse import CreateSessionResponse
from datetime import datetime, time, timezone
import tempfile


load_dotenv()

app = FastAPI(title="Excel RAG Session API")

# S3 & Remote Service Config
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "spread-sheet-repo")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://127.0.0.1:8000/execute")

s3_client = boto3.client("s3", region_name=AWS_REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

SESSION_STORE = {}  # In-memory session store; consider using a database for production

@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/sessions",response_model=CreateSessionResponse)
async def create_session():
    # Generate a unique session ID
    import uuid
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {"created_at": datetime.now(timezone.utc)}
    print(f"Session created: {session_id}")
    print(f"Current sessions: {SESSION_STORE}")
    return CreateSessionResponse(session_id=session_id, msg="Session created successfully.") 

@app.post("/sessions/{session_id}/upload")
async def upload_document(session_id:str, file: UploadFile = File(...) ):
    
    if session_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Save the uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir,file.filename) #generate a unique temp file name later
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())
    
    # Upload to S3
    s3_key = f"{session_id}/{file.filename}"
    s3_client.upload_file(temp_file_path, BUCKET_NAME, s3_key)
    
    # Generate a presigned URL for the uploaded file
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600  # URL valid for 1 hour
    )
    
    return {"message": "File uploaded successfully.", "presigned_url": presigned_url}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8001)