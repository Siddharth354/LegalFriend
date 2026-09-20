from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.api_errors import (
    PipelineError,
    pipeline_error_handler,
    unhandled_error_handler,
)
from src.core.config import settings
from src.core.logger import configure_logging, get_logger
from src.core.memory import Memory
from src.core.security import configure_cors
from src.modules.legal_notice.features.analyze.router import router as analyze_router
from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter
from src.runtime_api import router as runtime_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.memory = Memory(settings.sqlite_path)
    app.state.retrieval = RetrievalAdapter()
    app.state.retrieval.build_index()
    logger.info("startup_complete", collection=settings.collection_name)
    yield


app = FastAPI(title="LegalFriend", lifespan=lifespan)

configure_cors(app, extra_origins=settings.cors_extra_origins)
app.add_exception_handler(PipelineError, pipeline_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(runtime_router)
app.include_router(analyze_router)
