from aiogram import Dispatcher
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.const import ROOT_DIR, WEBAPP_PATH
from app.presentation.fastapi import healthcheck
from app.presentation.fastapi.api import router as api_router
from app.presentation.fastapi.api.errors import setup_errors

WEBAPP_DIR = ROOT_DIR / "webapp" / "dist"


def setup_fastapi(app: FastAPI, dispatcher: Dispatcher, container: AsyncContainer) -> FastAPI:
    app.include_router(healthcheck.router)
    app.include_router(api_router)
    setup_errors(app)
    for key, value in dispatcher.workflow_data.items():
        setattr(app.state, key, value)
    app.state.dispatcher = dispatcher
    app.state.shutdown_completed = False
    setup_dishka(container=container, app=app)
    if WEBAPP_DIR.is_dir():  # the built Mini App, served last so that it never shadows the API
        app.mount(WEBAPP_PATH, StaticFiles(directory=WEBAPP_DIR, html=True), name="webapp")
    return app
