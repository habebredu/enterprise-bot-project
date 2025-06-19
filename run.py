from fastapi.middleware.wsgi import WSGIMiddleware
from app import app
from api import app as fastapi_app

fastapi_app.mount("/", WSGIMiddleware(app))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)
