import os
import requests
from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI(title="Admin Panel")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

html_path = Path(__file__).parent / "index.html"
html_content = html_path.read_text(encoding="utf-8")

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001")

# Router for API proxy
router = APIRouter()

# Allowed proxy paths
ALLOWED_PROXIES = {
    "/chats": {"GET": [], "POST": []},
    "/messages/{chat_id}": {"GET": ["chat_id"]},
}


def proxy_request(method: str, path: str, **kwargs):
    url = f"{BACKEND_URL}/api{path}"
    if method == "GET":
        return requests.get(url, **kwargs)
    elif method == "POST":
        return requests.post(url, **kwargs)
    elif method == "PUT":
        return requests.put(url, **kwargs)
    elif method == "DELETE":
        return requests.delete(url, **kwargs)


# --- Proxy endpoints ---
@router.get("/api/chats")
def proxy_chats_list():
    res = proxy_request("GET", "/chats")
    return Response(content=res.text, status_code=res.status_code, media_type="application/json")


@router.post("/api/chats")
def proxy_chat_create(body: dict):
    res = proxy_request("POST", "/chats", json=body)
    return Response(content=res.text, status_code=res.status_code, media_type="application/json")


@router.delete("/api/chats/{chat_id}")
def proxy_chat_delete(chat_id: str):
    res = proxy_request("DELETE", f"/chats/{chat_id}")
    return Response(content=res.text, status_code=res.status_code, media_type="application/json")


@router.put("/api/chats/{chat_id}/rename")
def proxy_chat_rename(chat_id: str, body: dict):
    res = proxy_request("PUT", f"/chats/{chat_id}/rename", json=body)
    return Response(content=res.text, status_code=res.status_code, media_type="application/json")


@router.get("/api/messages/{chat_id}")
def proxy_messages(chat_id: str):
    res = proxy_request("GET", f"/messages/{chat_id}")
    return Response(content=res.text, status_code=res.status_code, media_type="application/json")


app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def admin_panel():
    return html_content
