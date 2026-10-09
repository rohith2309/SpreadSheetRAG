import os
import sys
import io
import urllib.request
import pandas as pd

SESSION_CACHE = {}


def lambda_handler(event, context):

    file_id = event.get("file_id")
    s3_link = event.get("file_url")
    code = event.get("code")

    if not file_id or not code:
        return {
            "status": "error",
            "error": "file_id and code are required."
        }

    # --------------------------------------------------
    # 1. Load Excel file
    # --------------------------------------------------

    try:

        if file_id in SESSION_CACHE:

            df = SESSION_CACHE[file_id]

        else:

            local_path = f"/tmp/{file_id}"

            if not os.path.exists(local_path):

                if not s3_link:
                    return {
                        "status": "error",
                        "error": "File not found locally or from S3."
                    }

                urllib.request.urlretrieve(
                    s3_link,
                    local_path
                )

            df = pd.read_excel(local_path)

            SESSION_CACHE[file_id] = df

    except Exception as e:

        return {
            "status": "error",
            "error": f"Failed to load Excel file: {str(e)}"
        }

    # --------------------------------------------------
    # 2. Execute generated pandas code
    # --------------------------------------------------

    output = io.StringIO()

    execution_vars = {
        "df": df.copy(deep=False),
        "pd": pd
    }

    original_stdout = sys.stdout
    sys.stdout = output

    try:

        exec(
            code,
            {
                "__builtins__": __builtins__
            },
            execution_vars
        )

        # Restore stdout
        sys.stdout = original_stdout

        # Get result variable
        result = execution_vars.get("result")

        # Get print() output
        stdout_output = output.getvalue().strip()

        # Prefer result variable
        final_output = (
            result
            if result is not None
            else stdout_output
        )

        return {
            "status": "success",
            "output": final_output
        }

    except Exception as e:

        sys.stdout = original_stdout

        return {
            "status": "error",
            "error": str(e)
        }