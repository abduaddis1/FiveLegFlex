from fastapi import FastAPI
from booksdata import getBestProps

app = FastAPI()


@app.get("/api/best-props")
async def read_best_props():
    return getBestProps()
