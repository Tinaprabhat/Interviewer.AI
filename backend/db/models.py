from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    candidate_name = Column(String, nullable=True)
    role = Column(String, nullable=False)
    resume_data = Column(JSON, nullable=True)
    state = Column(JSON, nullable=True)  # interview state machine data
    pending_question = Column(Text, nullable=True)  # JSON string, set by /next, cleared by /answer
    is_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id = Column(String, primary_key=True, default=gen_uuid)
    filename = Column(String, nullable=False)
    candidate_name = Column(String, nullable=True)
    parsed_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, nullable=False)
    question_number = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    step = Column(String, nullable=True)
    expected_concepts = Column(JSON, nullable=True)
    evaluation = Column(JSON, nullable=True)
    context_used = Column(Text, nullable=True)
    llm_provider = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, nullable=False, unique=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
