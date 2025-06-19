from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

security = HTTPBasic()

ADMIN_CREDENTIALS = {
    os.getenv("ADMIN_USERNAME"): os.getenv("ADMIN_PASSWORD")
}


def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password

    if username not in ADMIN_CREDENTIALS or ADMIN_CREDENTIALS[username] != password:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return username
