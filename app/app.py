from fastapi import FastAPI,File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
from dotenv import load_dotenv
from schemas.CreateSessionResponse import CreateSessionResponse
from datetime import datetime, time, timezone
import tempfile
import hashlib
import pandas as pd
from typing import List
import logging
import pprint
from langchain_core.messages import HumanMessage
from workflow.workflowExp import expgraph
from utility.GetUniqueval import get_unique_samples
from utility.extractSheet import extract_sheet_data

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()

app = FastAPI(title="Excel RAG Session API")
FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
        
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

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
    

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_hash =  hashlib.sha256(content).hexdigest()[:16]
    
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-=")
    
    # Upload to S3
    file_id=f"file_{file_hash}_{safe_filename}"
    
    # Save the uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir,file_id) #generate a unique temp file name later
    with open(temp_file_path, "wb") as f:
        f.write(content)
    
    s3_key = f"{session_id}/{file_id}"
    s3_client.upload_file(temp_file_path, BUCKET_NAME, s3_key)
    
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600  # URL valid for 1 hour
    )
    try:
        sheets_peek = extract_sheet_data(temp_file_path)

        columns = []
        row = 0
        column_type = {}
        unique = {}
        preview = []

        if safe_filename.lower().endswith((".xls", ".xlsx")):
            with pd.ExcelFile(temp_file_path) as xls:
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=20)
                    columns = list(df.columns)
                    row = df.shape[0]
                    column_type = df.dtypes.astype(str).to_dict()
                    unique = get_unique_samples(df)
                    preview = df.head(5).to_dict(orient="records")

        SESSION_STORE[session_id].setdefault("files", {})
        SESSION_STORE[session_id]["files"][safe_filename] = {
            # "meta_data": {
            #     "row_count": row,
            #     "preview": preview,
            #     "column_type": column_type,
            #     "columns": columns,
            #     "unique_vals": unique,
            # },
            "s3_url": presigned_url,
            "file_id": file_id,
            "sheet_names": list(sheets_peek.keys()),
            "sheets_peek": sheets_peek,
        }
        logging.info("======= session info =======")
        logging.info(SESSION_STORE[session_id]["files"])
        logging.info("======= session info ENDS =======")
    except Exception:
        logging.exception("Upload processing failed")
        raise
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)         
    
    return {"message": "File uploaded successfully.", "presigned_url": presigned_url}


@app.websocket("/ws/{session_id}")
async def test_workflow(websocket: WebSocket, session_id: str):
    origin = websocket.headers.get("origin")
    if origin and origin.rstrip("/") not in FRONTEND_ORIGINS and "*" not in FRONTEND_ORIGINS:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    session_data = SESSION_STORE.get(session_id)
    # FIX: Check for "files" dict instead of top-level "file_id"
    if not session_data or not session_data.get("files"):
        await websocket.send_json({"error": "Upload at least one file for this session before testing the workflow."})
        await websocket.close(code=1008)
        return

    logging.info("WS CONNECTED session=%s files=%s", session_id, list(session_data["files"].keys()))

    messages = []
    try:
        while True:
            payload = await websocket.receive_json()
            message = payload.get("message") if isinstance(payload, dict) else None
            if not isinstance(message, str) or not message.strip():
                await websocket.send_json({"error": "Send a JSON object with a non-empty 'message' string."})
                continue

            messages.append(HumanMessage(content=message))
            logging.info("QUESTION=%s session=%s", message, session_id)

            # FIX: Pass keys that match AgentStatev2 + recursion_limit for multi-step loops
            result = await expgraph.ainvoke(
                {
                    "session": session_id,
                    "files": session_data["files"],  # Dynamically reads all uploaded files in session
                    "messages": messages,
                },
                config={"recursion_limit": 25}
            )

            messages = list(result["messages"])
            response = next(
                (item for item in reversed(messages) if getattr(item, "type", None) == "ai"),
                None,
            )
            await websocket.send_json({
                "message": response.content if response else "Workflow returned no assistant message.",
            })
    except WebSocketDisconnect:
        logging.info("Workflow test websocket disconnected for session %s", session_id)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8001)
