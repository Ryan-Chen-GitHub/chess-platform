# Iterator is the type hint for a function that yields values one at a time.
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_session() -> Iterator[Session]:
    """Give each API request its own database session, then close it.

    FastAPI calls this "dependency injection": endpoints declare that they
    need a session, and FastAPI runs this function in response. Tests can
    swap it for an in-memory database without touching the endpoints.
    """
    # The "with" block guarantees the session is closed after the request,
    # even if the endpoint raised an error.
    with SessionLocal() as session:
        # yield hands the session to the endpoint, then resumes here when
        # the request finishes.
        yield session