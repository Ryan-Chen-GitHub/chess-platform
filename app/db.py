# create_engine builds the connection to the database; "event" lets us run
# code whenever a new connection opens.
from sqlalchemy import create_engine, event

# DeclarativeBase is the parent class for all our table definitions.
# sessionmaker creates "sessions", which are the objects we use to read and
# write rows.
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# The connection string. "sqlite:///chess.db" means a SQLite database stored
# in a file called chess.db. Moving to PostgreSQL later means changing only
# this line (plus installing a driver).
DATABASE_URL = "sqlite:///chess.db"

# The engine manages the actual connection(s) to the database.
engine = create_engine(DATABASE_URL)


# SQLite ignores foreign key rules by default, which would let us insert a
# game pointing at a player that doesn't exist. This runs on every new
# connection and turns enforcement on.
@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# A factory that creates sessions bound to our engine.
SessionLocal = sessionmaker(bind=engine)


# Every table class we write inherits from Base. SQLAlchemy uses it to keep
# track of all tables so it can create them together.
class Base(DeclarativeBase):
    pass