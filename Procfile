web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: uvicorn app.worker_app:app --host 0.0.0.0 --port $PORT
