from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, TIMESTAMP, func, Index)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from database.base import Base

# =======================================
# Project (프로젝트 메타 정보)
# - 프로젝트 기본 속성 관리
# =======================================
class Project(Base):
    __tablename__ = "project_table"

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(Integer, ForeignKey("user_table.id", ondelete="RESTRICT"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True, index=True)
    project_name = Column(String(255), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 관계: User ↔ Project (1:N)
    user = relationship("User", back_populates="projects")    ## 관례상 다수가 되는 projects로 작명
    model = relationship("AIModel", back_populates="projects")
    info_bases = relationship("ProjectInfoBase", back_populates="project", cascade="all,delete")  # 명시


# =======================================
# ProjectInfoBase (프로젝트 파일/지식베이스 메타)
# - project_table.project_id FK 참조
# - 프로젝트에 업로드된 파일 관리
# =======================================
# class ProjectInfoBase(Base):
#     __tablename__ = "project_info_base"
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     project_id = Column(Integer, ForeignKey("project_table.project_id", ondelete="CASCADE"), nullable=False, index=True)
#     uploaded_by_user_id = Column(Integer, ForeignKey("user_table.id", ondelete="SET NULL"),
#                                  nullable=True, index=True)
#     file_name = Column(String(255))
#     file_url = Column(Text, nullable=True)
#     upload_at = Column(TIMESTAMP, default=func.current_timestamp())
#
#     # 관계: Project ↔ ProjectInfoBase (1:N)
#     project = relationship("Project", backref="info")
#     uploader = relationship("User", backref="uploaded_info_bases")
#
#     # 관계: User ↔ ProjectInfoBase (1:N)
#     user = relationship("User", backref="project_info")

class ProjectInfoBase(Base):
    __tablename__ = "project_info_base"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK
    project_id = Column(Integer, ForeignKey("project_table.project_id", ondelete="CASCADE"), nullable=False, index=True)
    user_email = Column(String(255), ForeignKey("user_table.email", ondelete="CASCADE"), nullable=False)

    # 업로드 메타
    orig_name = Column(String(255))            # 원본 파일명
    file_path = Column(Text)                   # 서버 저장 경로
    size = Column(Integer)                     # 바이트 크기


    # 산출물
    output_folder = Column(Text)               # 산출물 폴더
    html_path = Column(Text)
    md_path = Column(Text)
    images = Column(ARRAY(Text))               # 렌더된 이미지 경로 리스트
    json_paths = Column(JSONB)                 # {pdf_path: json_path}
    parts = Column(ARRAY(Text))                # 분할된 파일 경로 리스트

    # 타임스탬프
    upload_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # 관계
    project = relationship("Project", backref="info")  # Project ↔ ProjectInfoBase (1:N)
    user = relationship("User", backref="project_info")  # User ↔ ProjectInfoBase (1:N)

# =======================================
# InfoList (세부 지식 단위 + 벡터 임베딩)
# - project_info_base.id FK 참조
# - pgvector.Vector(1536)로 임베딩 저장
# =======================================
# class InfoList(Base):
#     __tablename__ = "info_list"
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     infobase_id = Column(Integer, ForeignKey("project_info_base.id", ondelete="CASCADE"), nullable=False, index=True)
#     content = Column(Text)
#     vector_memory = Column(Vector(1536))
#     upload_at = Column(TIMESTAMP, default=func.current_timestamp())
#
#     # 관계: ProjectInfoBase ↔ InfoList (1:N)
#     infobase = relationship(
#         "ProjectInfoBase",
#         backref=backref("info_list", passive_deletes=True))

class InfoList(Base):
    __tablename__ = "info_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    infobase_id = Column(Integer, ForeignKey("project_info_base.id", ondelete="CASCADE"), nullable=False, index=True)

    content = Column(Text)
    meta_json = Column("metadata",JSONB)                   # {"page": 3, "section": "1.2", ...}
    vector_memory = Column(Vector(1536))

    upload_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    infobase = relationship(
        "ProjectInfoBase",
        backref=backref("info_list", passive_deletes=True))


# =======================================
# 권장 인덱스
# - JSONB GIN: 메타 필터
# - pgvector HNSW: 근접 검색 (사전 확장 필요: CREATE EXTENSION IF NOT EXISTS vector;)
#   Alembic에서 생성 권장. 예시는 주석 참고.
# =======================================

# JSONB GIN 인덱스 (Alembic에서 생성 추천)
Index("ix_info_list_metadata_gin", InfoList.meta_json, postgresql_using="gin")