from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import auth, booking, event


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code can go here (e.g., connect to external services)
    print("Starting up...")

    yield  # This is where the application runs

    # Shutdown code can go here (e.g., close connections)
    print("Shutting down...")


app = FastAPI(title="Event Booking API", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(event.router, prefix="/api/v1")
app.include_router(booking.router, prefix="/api/v1")


@app.get("/health")
async def root() -> dict[str, str]:
    return {"status": "Ok"}
