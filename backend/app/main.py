from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import projects, documents, summaries, chat
from .core import lifespan

app = FastAPI(title="AI Paper Summarizer", version="1.0.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://khai-pha-du-lieu-git-web-hoamattroi224s-projects.vercel.app",
        "https://khaiphadulieu-frontend.vercel.app",
        "https://khai-pha-du-lieu-dusky.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(summaries.router)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Academic Paper Summary AI System"}
