# CRUD/ingestion.py
from __future__ import annotations
from typing import Iterable, Sequence, Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

# 프로젝트의 실제 경로에 맞춰 import
from models.project import ProjectInfoBase, InfoList  # 예: models_project.py
from models.llm import AIModel  # 필요 시

# -----------------------------
# 유틸
# -----------------------------
def _assign_if_attr(obj: Any, **fields: Any) -> None:
    for k, v in fields.items():
        if hasattr(obj, k) and v is not None:
            setattr(obj, k, v)

# -----------------------------
# Infobase: 파일 메타 등록/조회/갱신
# -----------------------------
def create_infobase(
    db: Session,
    *,
    project_id: int,
    file_path: str,
    orig_name: str,
    size: int,
    mime: Optional[str] = None,
) -> ProjectInfoBase:
    ib = ProjectInfoBase()
    _assign_if_attr(
        ib,
        project_id=project_id,
        file_path=file_path,
        orig_name=orig_name,
        size=size,
        mime=mime,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(ib)
    db.commit()
    db.refresh(ib)
    return ib

def get_infobase(db: Session, infobase_id: int) -> Optional[ProjectInfoBase]:
    return db.get(ProjectInfoBase, infobase_id)

def list_infobases_by_project(db: Session, project_id: int) -> List[ProjectInfoBase]:
    stmt = select(ProjectInfoBase).where(ProjectInfoBase.project_id == project_id)
    return list(db.scalars(stmt))

def update_infobase_assets(
    db: Session,
    *,
    infobase_id: int,
    output_folder: Optional[str] = None,
    html_path: Optional[str] = None,
    md_path: Optional[str] = None,
    images: Optional[Sequence[str]] = None,
    json_paths: Optional[Dict[str, str]] = None,
) -> ProjectInfoBase:
    ib = db.get(ProjectInfoBase, infobase_id)
    if not ib:
        raise ValueError("infobase not found")

    # ProjectInfoBase에 해당 컬럼이 없으면 무시
    _assign_if_attr(
        ib,
        output_folder=output_folder,
        html_path=html_path,
        md_path=md_path,
        images=images,            # ARRAY(TEXT)나 JSONB 컬럼일 수 있음
        json_paths=json_paths,    # JSONB 컬럼일 수 있음
        updated_at=datetime.utcnow(),
    )
    db.add(ib)
    db.commit()
    db.refresh(ib)
    return ib

# -----------------------------
# InfoList: 청크+벡터 삽입/조회
# -----------------------------
def bulk_insert_chunks(
    db: Session,
    *,
    infobase_id: int,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """
    rows 예:
    {
      "content": "텍스트",
      "metadata": {"page": 3, "section": "1.2"},
      "vector_memory": [float, ...]  # pgvector
    }
    모델 필드명이 다르면 키를 맞춰 전달.
    """
    count = 0
    for r in rows:
        item = InfoList()
        _assign_if_attr(
            item,
            infobase_id=infobase_id,
            content=r.get("content"),
            meta_json=r.get("metadata") or r.get("meta_json"),
            vector_memory=r.get("vector_memory"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(item)
        count += 1
    db.commit()
    return count

def list_chunks(
    db: Session,
    *,
    infobase_id: int,
    limit: int = 100,
    offset: int = 0,
) -> List[InfoList]:
    stmt = (
        select(InfoList)
        .where(InfoList.infobase_id == infobase_id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))

# -----------------------------
# 파이프라인 단계 기록(선택)
# -----------------------------
def record_split_parts(
    db: Session,
    *,
    infobase_id: int,
    parts: Sequence[str],
) -> ProjectInfoBase:
    """
    ProjectInfoBase에 parts를 저장할 컬럼이 있을 때만 적용.
    """
    ib = db.get(ProjectInfoBase, infobase_id)
    if not ib:
        raise ValueError("infobase not found")
    _assign_if_attr(ib, parts=list(parts), updated_at=datetime.utcnow())
    db.add(ib)
    db.commit()
    db.refresh(ib)
    return ib

def record_analyze_mapping(
    db: Session,
    *,
    infobase_id: int,
    json_paths: Dict[str, str],
) -> ProjectInfoBase:
    """
    {pdf_path: json_path} 매핑을 저장. JSONB 컬럼(json_paths)이 있을 때만 동작.
    """
    ib = db.get(ProjectInfoBase, infobase_id)
    if not ib:
        raise ValueError("infobase not found")
    # 누적 저장을 원하면 병합
    existing = getattr(ib, "json_paths", None) or {}
    merged = {**existing, **json_paths}
    _assign_if_attr(ib, json_paths=merged, updated_at=datetime.utcnow())
    db.add(ib)
    db.commit()
    db.refresh(ib)
    return ib

# -----------------------------
# 업로드 응답 변환 헬퍼
# -----------------------------
def to_upload_response(ib: ProjectInfoBase) -> Dict[str, Any]:
    """
    SCHEMAS.ingestion.UploadResponse로 직렬화할 때 사용할 dict.
    실제 스키마에서 추가 필드가 있으면 맞춰 확장.
    """
    return {
        "filename": getattr(ib, "orig_name", None) or getattr(ib, "filename", ""),
        "path": getattr(ib, "file_path", ""),
        "size": getattr(ib, "size", 0),
    }
