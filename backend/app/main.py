from fastapi import FastAPI

app = FastAPI(title="SwingLens API")


@app.get("/health")
def health():
    return {"status": "ok"}
