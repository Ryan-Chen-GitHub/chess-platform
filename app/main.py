# Web Framework, turns Python functions --> HTTP endpoints
from fastapi import FastAPI

# Application object, Title used for auto-generated docs page at /docs
app = FastAPI(title="Chess Platform")

# Health check to make sure the service isn't exploding
# and also turns dictionary --> JSON
@app.get("/health")
def health():
    return {"status": "ok"}