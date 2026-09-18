from fastapi import FastAPI
from schema.CodeSnippet import CodeSnippet
import subprocess
import tempfile

app = FastAPI(title="Python Code Execution Server")


@app.get("/health")
async def root():
    return {"message": "Server is running!"}

@app.post("/execute")
async def execute_code(code_snippet: CodeSnippet):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code_snippet.code)
        script_path = f.name
        
    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
            
        return {"status": "success", "output": output if output.strip() else "Success: No output."}
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Execution timed out."}
    except Exception as e:
        return {"status": "error", "output": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)