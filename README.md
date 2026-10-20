# SpreadsheetRAG

SpreadsheetRAG is a Python application that lets you chat with spreadsheet data in natural language. Upload a spreadsheet, extract schema metadata, and ask questions like "What is the total revenue by region?" or "Which department has the highest spend?" The backend uses a LangChain/LangGraph workflow, generates pandas code, and executes it in an AWS Lambda environment for safe, isolated analysis.

## Features

- Upload `.xlsx`, `.xls`, or `.csv` files
- Create a session-bound workflow for each spreadsheet
- Extract table metadata, column types, and sample values
- Chat over a WebSocket endpoint
- Generate and execute Python analysis code with pandas
- Use AWS S3 for uploaded file storage and AWS Lambda for execution
- Simple static frontend for local testing and demos

## Architecture

The project is structured around a FastAPI backend and a LangGraph-based agent workflow:

1. A session is created via the API.
2. The spreadsheet is uploaded and stored in S3.
3. The uploaded file is read into a pandas DataFrame to extract metadata.
4. The user sends a natural-language question over WebSocket.
5. The workflow generates Python code using pandas.
6. The generated code is executed in AWS Lambda.
7. The result is returned to the frontend or client.

## Project structure

```text
.
├── app/
│   ├── Agents/
│   ├── Lambda/
│   ├── Tools/
│   ├── config/
│   ├── schemas/
│   ├── utility/
│   ├── workflow/
│   └── app.py
├── frontend/
│   ├── app.js
│   ├── config.js
│   ├── index.html
│   └── styles.css
├── code-exec-backend/
├── deploy/
├── main.py
├── README.md
├── pyproject.toml
├── .env.example
├── vercel.json
└── uv.lock
```

## Prerequisites

- Python 3.12+
- `uv` package manager
- AWS credentials for S3 and Lambda access
- A configured S3 bucket

## Setup

1. Clone the repository
2. Create a local environment file from the example:

```bash
cp .env.example .env
```

3. Fill in your AWS and app settings in `.env`:

```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION_NAME=us-east-1
S3_BUCKET_NAME=your_bucket_name
```

4. Install dependencies:

```bash
uv sync
```

## Run the backend

From the project root:

```bash
uv run python app/app.py
```

The backend will start on:

```text
http://127.0.0.1:8001
```

You can also run it with Uvicorn directly:

```bash
uv run uvicorn app.app:app --reload --port 8001
```

## Run the frontend

There are two common options:

1. Open the static frontend in a browser with a local file server:

```bash
cd frontend
python -m http.server 3000
```

Then visit:

```text
http://127.0.0.1:3000
```

2. Use a VS Code Live Server or another static-file host.

## API endpoints

### Create a session

```http
GET /sessions
```

Example response:

```json
{
  "session_id": "<uuid>",
  "msg": "Session created successfully."
}
```

### Upload spreadsheet

```http
POST /sessions/{session_id}/upload
```

Send a multipart form with a spreadsheet file.

### WebSocket chat

```text
ws://127.0.0.1:8001/ws/{session_id}
```

Example payload:

```json
{
  "message": "What is the budget of the sales department?"
}
```

The backend will respond with the generated result from the workflow.

## Workflow overview

1. Create a session.
2. Upload the spreadsheet to S3.
3. Read the file and extract schema metadata.
4. Ask a question using the WebSocket chat endpoint.
5. The agent generates pandas code.
6. The code is passed to a Lambda-based execution environment.
7. The result is returned to the user.

## Example usage

### Create a session

```bash
curl http://127.0.0.1:8001/sessions
```

### Upload a spreadsheet

```bash
curl -X POST "http://127.0.0.1:8001/sessions/<session_id>/upload" \
  -F "file=@sales_data.xlsx"
```

### Ask a question

Use the WebSocket at `ws://127.0.0.1:8001/ws/<session_id>` and send:

```json
{ "message": "Show total revenue by region." }
```

## Notes

- This project is experimental and currently optimized around a single spreadsheet file/session flow.
- The code execution path is designed to keep agent-generated logic isolated and executable in a serverless environment.
- The app can be extended with validation agents, smarter intent routing, multi-file support, and multi-sheet ingestion.

## Roadmap

- Add a validation agent for generated code safety
- Add intent routing and retrieval-based improvements
- Support multiple spreadsheets and multiple sheets in a single dataset
- Improve session persistence and production readiness

## License

This project does not currently declare a project license in the repository metadata. If you plan to distribute it publicly, consider adding a license file and updating the package metadata accordingly.


