from fastapi import FastAPI, HTTPException

from app.database import get_readonly_connection, get_admin_connection
from app.optimizer.sql_parser import SQLValidationError
from app.schemas import OptimizeRequest
from app.services.recommendation_service import optimize_query

app = FastAPI(title="QueryPilot")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize")
def optimize(req: OptimizeRequest):

    with get_readonly_connection() as ro, get_admin_connection() as admin:
        try:
            return optimize_query(ro, admin, req.sql)
        except SQLValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))