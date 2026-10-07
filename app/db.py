# "create_engine" allows for connection to the database
# "event" lets code run when a new connection is formed.
# "DeclarativeBase" is the parent class for all table definitions
# "sessionmaker" creates "sessions" aka objects used to read and write rows
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Stores database in a file called "chess.db"
# "engine" manages the connection to the database
DATABASE_URL = "sqlite:///chess.db"
engine = create_engine(DATABASE_URL)

# Tells SQLite to actually pay attention to foreign keys
# Otherwise games could point to players that don't exist
@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_key=ON")
    cursor.close()

# Creates sessions bound to the engine
# local where? ;-;
SessionLocal = sessionmaker(bind=engine)

# Makes sure all tables are created together
class Base(DeclarativeBase):
    pass