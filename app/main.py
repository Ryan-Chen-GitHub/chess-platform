# Web Framework, turns Python functions --> HTTP endpoints
# The router holds the endpoints we defined in routes.py.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

# Application object, Title used for auto-generated docs page at /docs
app = FastAPI(title="Chess Platform")
# Browsers block cross-origin reads unless the server opts in. Only the local
# front-end dev server is allowed, and only for read-only requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=[],
)

# Plug in all the endpoints from routes.py.
app.include_router(router)

# Health check to make sure the service isn't exploding
# and also turns dictionary --> JSON
@app.get("/health")
def health():
    return {"status": "ok"}