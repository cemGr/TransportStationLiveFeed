import os
import psycopg2


def open_connection():
    """Create a new database connection using environment variables."""
    try:
        return psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", 5432)),
            user=os.environ.get("PGUSER", "radverkehr"),
            password=os.environ.get("PGPASSWORD", "passwort123"),
            database=os.environ.get("PGDATABASE", "radstationen"),
            connect_timeout=int(os.environ.get("PGCONNECT_TIMEOUT", 5)),
        )
    except psycopg2.OperationalError as e:  # pragma: no cover - runtime feedback
        raise RuntimeError(
            "Datenbankverbindung fehlgeschlagen. Ist die Datenbank gestartet?"
        ) from e
