import os
import psycopg2


def open_connection():
    """Create a new database connection using environment variables."""
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ.get("PGUSER", "radverkehr"),
        password=os.environ.get("PGPASSWORD", "passwort123"),
        database=os.environ.get("PGDATABASE", "radstationen"),
    )
