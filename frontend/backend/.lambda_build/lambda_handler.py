"""AWS Lambda entrypoint for API Gateway HTTP API (proxy integration)."""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
