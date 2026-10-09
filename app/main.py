# Web Framework, turns Python functions --> HTTP endpoints
# The router holds the endpoints we defined in routes.py.
from fastapi import FastAPI

from app.routes import router

# Application object, Title used for auto-generated docs page at /docs
app = FastAPI(title="Chess Platform")

# Plug in all the endpoints from routes.py.
app.include_router(router)

# Health check to make sure the service isn't exploding
# and also turns dictionary --> JSON
@app.get("/health")
def health():
    return {"status": "ok"}