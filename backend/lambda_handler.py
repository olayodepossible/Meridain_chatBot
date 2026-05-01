from mangum import Mangum

from app.main import app

# Mangum is python package that helps to deploy FastAPI applications to AWS Lambda.
# It is a wrapper around the FastAPI application that makes it easier to deploy to AWS Lambda.
handler = Mangum(app)
