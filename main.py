import base64
import json
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

USERINFO_ENDPOINTS = {
    "bmw": "https://emea.int.alpha.sso.bmwgroup.com/auth/oauth2/realms/root/realms/alpha/userinfo",
    "keycloak": "https://6qqnl82r-8080.euw.devtunnels.ms/realms/demo/protocol/openid-connect/userinfo",
}


class UserInfoProvider(str, Enum):
    bmw = "bmw"
    graph = "keycloak"


async def get_user_info(access_token: str, provider: UserInfoProvider = UserInfoProvider.bmw) -> dict:
    url = USERINFO_ENDPOINTS[provider]
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


@app.get("/api/userinfo")
async def user_info(request: Request, provider: UserInfoProvider = UserInfoProvider.bmw):
    # Extract the access token from the x-ms-token-demo-access-token header
    access_token = request.headers.get("x-ms-token-demo-access-token")
    if not access_token:
        raise HTTPException(status_code=400, detail="x-ms-token-demo-access-token header is missing")
    try:
        return await get_user_info(access_token, provider)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch user info: {e.response.text}")

    

@app.get("/api/headers")
async def get_headers(request: Request):
    return dict(request.headers)


@app.get("/api/token")
async def get_token(request: Request):
    principal = request.headers.get("x-ms-client-principal")
    if not principal:
        raise HTTPException(status_code=400, detail="x-ms-client-principal header is missing")
    try:
        decoded = base64.b64decode(principal).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse token: {e}")

