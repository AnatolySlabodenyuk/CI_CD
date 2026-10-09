import os

from fastapi import FastAPI
import psycopg2
import redis

app = FastAPI()
redis_client = redis.Redis.from_url(
    os.environ["REDIS_URL"], socket_connect_timeout=5, socket_timeout=5
)


@app.get("/")
def read_root():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()[0]
    finally:
        conn.close()

    # INCR returns the new value atomically, including concurrent requests.
    visit_count = str(redis_client.incr("visit_count"))
    return {
        "message": "Приложение работает, юхуху!",
        "postgres_version": db_version,
        "visit_count": visit_count,
    }


@app.get("/health")
def health_check():
    # Liveness check, as in the lecture; dependency readiness is tested separately.
    return {"status": "healthy"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
