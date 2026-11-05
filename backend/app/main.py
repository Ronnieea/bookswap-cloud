from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.routers.books import router as books_router
from app.routers.external import router as external_router
from app.routers.exchanges import router as exchanges_router


app = FastAPI(
    title="BookSwap Cloud API",
    description="A cloud-based book exchange platform",
    version="1.0.0"
)


# CORS 設定：允許前端跨來源呼叫 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


app.include_router(books_router)
app.include_router(external_router)
app.include_router(exchanges_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to BookSwap Cloud!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# 保留 API Gateway /prod Stage 路徑處理
handler = Mangum(app, api_gateway_base_path="/prod")