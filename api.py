from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, Response
from starlette.responses import HTMLResponse, RedirectResponse
from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

import threading
from pathlib import Path
import shutil
from typing import List


from ticket_manager import DatabaseHandler
from unknown_manager import ADMIN, send_email, background_ticket_watcher
from chatbot import ask_bot, TEMP_CHAT_HISTORY
import schemas
from vector import process_file

# TODO: Temporary, make more secure later
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


security = HTTPBasic()
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def verify_admin(request: Request):
    session = request.cookies.get("admin_session")
    if session != "valid_admin_session":
        raise HTTPException(
            status_code=302,
            headers={"Location": "/xhSHIH720nshLOGIN"}
        )
    return "admin"


@app.post("/admin_login")
def admin_login(response: Response):
    response.set_cookie(
        key="admin_session",
        value="valid_admin_session",
        httponly=True,   # JS can't access this cookie (more secure)
        max_age=3600     # 1 hour expiry
    )
    return {"success": True}


@app.get("/xhSHIH720nshLOGOUT")
async def admin_logout():
    response = RedirectResponse(url="/xhSHIH720nshLOGIN", status_code=302)
    response.delete_cookie("admin_session")
    return response


@app.get("/xhSHIH720nshADMIN", response_class=HTMLResponse)
def admin_dashboard(request: Request, username: str = Depends(verify_admin)):
    with DatabaseHandler() as db:
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "user": username,
            "tickets": db.tickets_as_dict()
        })


@app.get("/xhSHIH720nshLOGIN", response_class=HTMLResponse)
def login_page(request: Request):
    session_cookie = request.cookies.get("admin_session")
    if session_cookie == "valid_admin_session":
        return RedirectResponse(url="/xhSHIH720nshADMIN", status_code=302)

    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.get("/xhSHIH720nshADMIN/upload", response_class=HTMLResponse)
def get_upload(request: Request, username: str = Depends(verify_admin)):
    return templates.TemplateResponse("upload.html", {"request": request, "user": username})


@app.post("/upload_file")
async def upload_file(files: List[UploadFile] = File(...), _: str = Depends(verify_admin)):
    for file in files:
        allowed_types = ["application/pdf",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         "text/plain"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

        upload_dir = Path("uploaded_files")
        upload_dir.mkdir(exist_ok=True)

        filepath = upload_dir / file.filename
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Call vector processing
        process_file(str(filepath))

    return RedirectResponse(
        url=f"/xhSHIH720nshADMIN/upload?success=true",
        status_code=303
    )


@app.on_event("startup")
def start_background_thread():
    email_thread = threading.Thread(target=background_ticket_watcher, daemon=True)
    email_thread.start()


"""
@app.post("/generate_ticket")
def create_ticket(info: schemas.EmailInput):
    print(info.email)
    with DatabaseHandler() as db:
        ticket_name = db.generate_ticket(info.email)
        return {"ticket_name": ticket_name}
"""


@app.post("/ask")
async def ask_question(request: schemas.AskRequest):
    ticket_name = request.ticket_name
    question = request.question

    if not ticket_name:
        TEMP_CHAT_HISTORY.append({'role': "user", "message": question})
    else:
        with DatabaseHandler() as db:
            db.append_history('history_user', ticket_name, 'user', question)

    answer, send = ask_bot(question, ticket_name)

    return JSONResponse(content={
        "answer": answer,
        "send": send
    })


@app.post("/escalate")
async def escalate_chat(escalation: schemas.EmailInput):
    print('escalated')
    email = escalation.email

    with DatabaseHandler() as db:
        ticket_name = db.generate_ticket(email, TEMP_CHAT_HISTORY)

    send_email(ADMIN, ticket_name)

    return JSONResponse(content={"ticket_name": ticket_name})
