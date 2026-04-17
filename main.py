import base64
import json
import os
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

ACCESS_TOKEN_HEADER = os.environ.get("ACCESS_TOKEN_NAME", "x-ms-token-demo-access-token")

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


@app.get("/api/userinfo/data")
async def user_info_data(request: Request, provider: UserInfoProvider = UserInfoProvider.bmw):
    access_token = request.headers.get(ACCESS_TOKEN_HEADER)
    if not access_token:
        raise HTTPException(status_code=400, detail=f"{ACCESS_TOKEN_HEADER} header is missing")
    try:
        return await get_user_info(access_token, provider)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Access token expired. Call /.auth/refresh to obtain a new token and retry.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch user info: {e.response.text}")


@app.get("/api/userinfo", response_class=HTMLResponse)
async def user_info(provider: UserInfoProvider = UserInfoProvider.bmw):
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>User Info</title>
  <style>
    body {{ font-family: monospace; padding: 2rem; background: #f5f5f5; }}
    pre {{ background: #fff; border: 1px solid #ddd; padding: 1rem; border-radius: 4px; overflow: auto; }}
    #status {{ margin-bottom: 1rem; color: #555; }}
    #countdown {{ font-weight: bold; color: #007acc; }}
    .error {{ color: red; }}
  </style>
</head>
<body>
  <h2>User Info</h2>
  <div id="status">Next token refresh in <span id="countdown">60</span>s</div>
  <pre id="output">Loading...</pre>

  <script>
    const provider = "{provider.value}";
    const REFRESH_INTERVAL = 60;

    async function fetchUserInfo() {{
      try {{
        const res = await fetch(`/api/userinfo/data?provider=${{provider}}`);
        const data = await res.json();
        document.getElementById("output").textContent = JSON.stringify(data, null, 2);
        document.getElementById("output").className = "";
      }} catch (err) {{
        document.getElementById("output").textContent = String(err);
        document.getElementById("output").className = "error";
      }}
    }}

    async function refreshToken() {{
      await fetch("/.auth/refresh");
      await fetchUserInfo();
    }}

    let secondsLeft = REFRESH_INTERVAL;
    function tick() {{
      secondsLeft--;
      document.getElementById("countdown").textContent = secondsLeft;
      if (secondsLeft <= 0) {{
        secondsLeft = REFRESH_INTERVAL;
        refreshToken();
      }}
    }}

    fetchUserInfo();
    setInterval(tick, 1000);
  </script>
</body>
</html>
""")


    

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

