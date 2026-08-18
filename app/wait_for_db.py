"""Polls the configured database until it accepts connections, then exits."""
import sys
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .database import engine

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2


def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return 0
        except OperationalError:
            print(f"Waiting for database... ({attempt}/{MAX_ATTEMPTS})")
            time.sleep(DELAY_SECONDS)
    print("Database did not become ready in time.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
