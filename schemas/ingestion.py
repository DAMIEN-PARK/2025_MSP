import os
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# 업로드 완료 시 파일 메타 반환
class UploadResponse(BaseModel):
    """업로드 결과: 파일명, 저장 경로, 바이트 크기"""
    filename: str
    path: str
    size: int

# PDF 분할 요청 파라미터
class SplitRequest(BaseModel):
    """분할 대상 PDF 경로와 배치 크기"""
    pdf_path: str
    batch_size: int = 10

# PDF 분할 결과
class SplitResponse(BaseModel):
    """분할된 PDF 파일 경로 리스트"""
    parts: List[str]

# Upstage 레이아웃 분석 요청
class AnalyzeRequest(BaseModel):
    """분석할 PDF 경로들과 API 키(미지정 시 .env에서 로드)"""
    pdf_paths: List[str]
    upstage_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("UPSTAGE_API_KEY")
    )

# Upstage 레이아웃 분석 결과
class AnalyzeResponse(BaseModel):
    """원본 PDF 경로 → 생성된 JSON 경로 매핑"""
    json_paths: Dict[str, str]  # {pdf_path: json_path}

# Asset 추출 및 렌더 요청
class ExtractRequest(BaseModel):
    """원본 PDF 경로(동일 prefix의 *.json 자동 탐색)"""
    pdf_path: str  # 같은 prefix의 *.json 을 자동 탐색

# Asset 추출 및 렌더 결과
class ExtractResponse(BaseModel):
    """산출물 폴더, 생성된 이미지 목록, HTML/MD 경로"""
    output_folder: str
    images: List[str]
    html_path: str
    md_path: str

# end-to-end 파이프라인 실행 요청
class RunRequest(BaseModel):
    """PDF → 분할→분석→추출→HTML/MD까지 원샷 실행"""
    pdf_path: str
    batch_size: int = 10
    upstage_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("UPSTAGE_API_KEY")
    )

# end-to-end 파이프라인 실행 결과
class RunResponse(BaseModel):
    """분할 파트, JSON 매핑, 산출물 폴더, HTML/MD, 이미지 목록"""
    parts: List[str]
    json_paths: Dict[str, str]
    output_folder: str
    html_path: str
    md_path: str
    images: List[str]

