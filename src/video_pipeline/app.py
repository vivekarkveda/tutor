from fastapi import FastAPI
from video_pipeline.routes import (
    search_routes,
    file_routes,
    generator_routes,
    write_routes,
    video_routes
)

app = FastAPI(title="🎬 Modular Video Processing Pipeline API")

# ✅ Make sure write_routes is included
app.include_router(search_routes.router)
app.include_router(file_routes.router)
app.include_router(generator_routes.router)
app.include_router(write_routes.router)   # 👈 important
app.include_router(video_routes.router)

@app.get("/")
def root():
    return {"message": "🚀 Modular Video Pipeline API Running!"}
