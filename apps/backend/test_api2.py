from fastapi import FastAPI

app = FastAPI()

@app.get("/ping2")
def ping2():
    return {"ping2": "pong2"}
