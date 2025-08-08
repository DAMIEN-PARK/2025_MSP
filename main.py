from fastapi import FastAPI
from api.routers import router
from fastapi.middleware.cors import CORSMiddleware
from core.config import UPLOAD_FOLDER
from fastapi.staticfiles import StaticFiles
import os
import uvicorn

app = FastAPI(debug=True)

app.mount("/file", StaticFiles(directory="file"), name="file")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인에서 접근 허용, 실제 운영 환경에서는 특정 도메인만 허용하는 것이 좋음
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(router)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=5000)



#  테스트

#2025-08-08 영빈 테스트
#다시 테스트 임영빈
#2025-08-08 인식 테스트

#1차 수정
## 추가 수정 라인
### 병합 추가 수정 라인
