# Spreadsheet assistant UI

The frontend is a standalone static site built with plain HTML, CSS, and JavaScript. It can be deployed independently of the FastAPI backend.

## Local development

```powershell
uvicorn app.app:app --reload --port 8001
```

Serve this folder with any static-file server, then open the local frontend URL. For example:

```powershell
python -m http.server 3000 --directory frontend
```

The local API URL is configured in [config.js](./config.js).

## Deploy separately

1. Deploy the `frontend` folder to Vercel as a static site (Framework Preset: **Other**; no build command or output directory is needed).
2. In `frontend/config.js`, set `API_BASE_URL` to the public HTTPS URL of the FastAPI service deployed on AWS, then redeploy the frontend. This URL is public client-side configuration, not a secret.
3. Set `FRONTEND_ORIGINS` in the AWS backend environment to the exact Vercel site origin, for example `https://your-project.vercel.app`. For multiple trusted origins, provide a comma-separated list.
4. Expose the API over HTTPS and allow WebSocket connections through the AWS load balancer/proxy. The frontend automatically uses `wss://` for the chat connection when the API URL is HTTPS.

Create a session, upload an `.xlsx` or `.xls` file, and ask questions in the chat.
