import os
import random
import time
from datetime import datetime, timedelta, timezone

import psycopg

# Admin connection (only this user can insert). Development values only.
DB_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql://querypilot:querypilot_dev@localhost:5432/querypilot",
)

ROW_COUNT = 500_000
USER_COUNT = 50_000
STATUSES = ["completed", "pending", "failed"]
STATUS_WEIGHTS = [85, 10, 5]   # most transactions complete, few fail


def make_row(now: datetime) -> tuple:
    user_id = random.randint(1, USER_COUNT)
    amount = round(max(1.0, random.lognormvariate(3.5, 1.0)), 2)
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
    created_at = now - timedelta(seconds=random.randint(0, 365 * 24 * 3600))
    return (user_id, amount, status, created_at)


def main() -> None:
    random.seed(42)   # same data every run
    now = datetime.now(timezone.utc)
    start = time.time()

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Start clean so running the script twice doesn't double the data
            cur.execute("TRUNCATE transactions RESTART IDENTITY")

            # COPY streams all rows in one go, much faster than row-by-row INSERT
            with cur.copy(
                "COPY transactions (user_id, amount, status, created_at) FROM STDIN"
            ) as copy:
                for _ in range(ROW_COUNT):
                    copy.write_row(make_row(now))

            # Refresh table statistics so EXPLAIN plans look realistic
            cur.execute("ANALYZE transactions")
        conn.commit()

    print(f"Inserted {ROW_COUNT:,} rows in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()