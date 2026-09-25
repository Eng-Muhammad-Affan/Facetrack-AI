## ____ Routes ...
from app.features.auth import routes as auth_routes
from app.features.attendance_log import routes as log_routes
from app.features.users import routes as users_routes

from fastapi import FastAPI

from app.core.database import Base, engine

from fastapi.openapi.models import APIKey, APIKeyIn, SecuritySchemeType
from fastapi.openapi.utils import get_openapi

from starlette.requests import Request
from app.core.logger import logger
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from fastapi.middleware.cors import CORSMiddleware

from app.core.vector import enable_pgvector_extension

app = FastAPI()

from dotenv import load_dotenv
import os 

load_dotenv()

origins = os.getenv("ALLOWED_ORIGINS").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    ip = request.client.host
    method = request.method
    path = request.url.path
    logger.info(f"[{ip}] {method} {path}")
    response = await call_next(request)
    return response


enable_pgvector_extension(engine)
Base.metadata.create_all(bind=engine)  # Create tables

@app.get("/")
def health():
    return {"status": "healthy", "message": "Server is running smoothly"} 

# Your existing router inclusions continue below...
app.include_router(auth_routes.router)
app.include_router(log_routes.router)
app.include_router(users_routes.router)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"ERROR {exc.status_code} at {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )


# Swagger customization
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="E-Commerce API",
        version="1.0.0",
        description="Backend with FastAPI",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "CookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token"
        }
    }
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if "security" not in openapi_schema["paths"][path][method]:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
