# api/endpoints/ingestion.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database.session import get_db
from core.config import UPLOAD_FOLDER
from pathlib import Path
from typing import List, Dict, Any, Optional
import os

# 기존 CRUD/유틸
from crud.llm import upload_file as crud_upload_file, save_info
from langchain_service.chain.file_chain import get_file_chain
from langchain_service.embedding.get_vector import text_to_vector
from service.sms.generate_random_code import generate_verification_code

ingestion_router = APIRouter(prefix="/ingestion", tags=["ingestion"])

# -----------------------------
# 업로드: 파일 저장 + project_info_base 등록
# -----------------------------
@ingestion_router.post("/upload")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    project_id: int = Form(...),
    user_email: str = Form(...),
    session_id: Optional[str] = Form(None),
    subdir: str = Form("ingestion"),  # 저장 하위폴더
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF만 허용합니다.")

    # 저장 경로
    base_dir = os.path.join(UPLOAD_FOLDER, user_email, subdir)
    os.makedirs(base_dir, exist_ok=True)

    origin = file.filename
    token = generate_verification_code()
    saved_name = f"{project_id}_{token}_{origin}"
    saved_path = os.path.join(base_dir, saved_name)

    # 실제 저장
    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    # DB 기록(project_info_base)
    infobase_id = crud_upload_file(
        db=db, project=project_id, email=user_email, url=saved_path, name=origin
    )

    return JSONResponse(
        content={
            "filename": origin,
            "path": saved_path,
            "size": len(content),
            "infobase_id": infobase_id,
        }
    )

# -----------------------------
# 인제스트: 파일→텍스트→청크→벡터→info_list 저장
# -----------------------------
@ingestion_router.post("/ingest")
async def ingest_pdf(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Request JSON:
    {
      "project_id": int,
      "user_email": str,
      "pdf_path": str,          # 이미 서버에 저장된 경로
      "infobase_id": int|null,  # 없으면 새로 project_info_base에 등록
      "chunk_chars": 1200,
      "overlap": 200
    }
    """
    project_id = body.get("project_id")
    user_email = body.get("user_email")
    pdf_path: str = body.get("pdf_path")
    infobase_id: Optional[int] = body.get("infobase_id")
    chunk_chars: int = int(body.get("chunk_chars", 1200))
    overlap: int = int(body.get("overlap", 200))

    if not (project_id and user_email and pdf_path):
        raise HTTPException(status_code=422, detail="project_id, user_email, pdf_path는 필수입니다.")

    p = Path(pdf_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="pdf_path가 존재하지 않습니다.")

    # infobase 없으면 등록
    if not infobase_id:
        infobase_id = crud_upload_file(
            db=db, project=project_id, email=user_email, url=str(p), name=p.name
        )

    # 텍스트 추출
    # get_file_chain은 파일 경로를 받아 전체 텍스트를 반환하는 프로젝트 내 유틸이다.
    full_text: str = get_file_chain(db=db, id=infobase_id, file_path=str(p))

    # 단순 청킹
    chunks = _split_text(full_text, chunk_chars=chunk_chars, overlap=overlap)

    # 벡터화 + 저장
    saved = 0
    for ch in chunks:
        vec = text_to_vector(ch)
        save_info(db=db, infobase_id=infobase_id, content=ch, vector_memory=vec)
        saved += 1

    return JSONResponse(
        content={
            "infobase_id": infobase_id,
            "chunks_saved": saved,
            "chunk_chars": chunk_chars,
            "overlap": overlap,
        }
    )

# -----------------------------
# 청크 조회(디버그/검증 용도)
# -----------------------------
@ingestion_router.get("/chunks")
async def list_chunks(
    infobase_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from models.project import InfoList

    q = (
        select(InfoList)
        .where(InfoList.infobase_id == infobase_id)
        .order_by(InfoList.id.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(q).scalars().all()
    return [
        {
            "id": r.id,
            "content_preview": (r.content[:200] + ("…" if len(r.content) > 200 else "")) if r.content else "",
            "upload_at": r.upload_at,
        }
        for r in rows
    ]


# -----------------------------
# 내부 유틸: 간단 청킹
# -----------------------------
def _split_text(text: str, *, chunk_chars: int = 1200, overlap: int = 200) -> List[str]:
    if not text:
        return []
    text = text.replace("\r\n", "\n")
    chunks: List[str] = []
    start = 0
    n = len(text)
    step = max(1, chunk_chars - overlap)
    while start < n:
        end = min(n, start + chunk_chars)
        # 문장 경계 근사 조정
        slice_ = text[start:end]
        if end < n:
            last_dot = slice_.rfind(".")
            last_kr = max(slice_.rfind("다."), slice_.rfind("다\n"))
            candidate = max(last_dot, last_kr)
            if candidate > chunk_chars // 3:
                end = start + candidate + 1
                slice_ = text[start:end]
        chunks.append(slice_.strip())
        start = end - overlap
        if start < 0:
            start = 0
        if start >= n:
            break
    # 공백 제거
    return [c for c in (s.strip() for s in chunks) if c]
