import json
import sys

from app.database import get_readonly_connection, get_admin_connection
from app.services.recommendation_service import optimize_query


def fake_model(analysis):
    return {
        "explanation": "Fake answer for testing.",
        "candidate_sql": "SELECT id FROM transactions WHERE user_id = 42",
        "index_suggestions": [
            "CREATE INDEX idx_tx_user ON transactions (user_id)",
            "DROP TABLE transactions",       # must be rejected
        ],
    }


sql = "SELECT id FROM transactions WHERE user_id = 42"
ro, admin = get_readonly_connection(), get_admin_connection()

if "--real" in sys.argv:
    result = optimize_query(ro, admin, sql)
else:
    result = optimize_query(ro, admin, sql, suggest=fake_model)

print(json.dumps(result, indent=2, default=str))