from fastapi import FastAPI

app = FastAPI(title="Subscription Platform")

@app.get("/health")
def health_check():
    return {"status": "ok"}
