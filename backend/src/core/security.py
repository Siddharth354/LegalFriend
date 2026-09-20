from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def configure_cors(app: FastAPI, extra_origins: list[str] | None = None) -> None:
    origins = FRONTEND_ORIGINS + (extra_origins or [])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
