# Importing models registers every table class with Base
# telling create_all what to build, otherwise it makes nothing
from app import models # noqa: F401
from app.db import Base, engine

# create_all builds any tables that don't exist yet, skipping
# tables that already exist.
Base.metadata.create_all(engine)
print("Tables created:", ", ".join(Base.metadata.tables))
