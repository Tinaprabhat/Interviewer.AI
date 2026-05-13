from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    database_url: str = "sqlite:///./data/pgagi_interview.db"
    chroma_persist_dir: str = "./data/chroma_db"
    kb_dir: str = "./data/kb_pdfs"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()

# Knowledge base PDFs to auto-fetch (role -> list of {name, url})
KB_SOURCES = {
    "AI/ML Engineer": [
        {
            "name": "machine_learning_tom_mitchell.pdf",
            "url": "https://cdn.chools.in/DIG_LIB/E-Book/M1-Machine-Learning-Tom-Mitchell_.pdf",
        },
        {
            "name": "hundred_page_ml_book_burkov.pdf",
            "url": "https://raw.githubusercontent.com/Nixtla/nixtla/main/experiments/foundation-time-series-arena/data/the-hundred-page-machine-learning-book.pdf",
            "fallback_url": None,
        },
    ],
    "Backend Engineer": [
        {
            "name": "machine_learning_tom_mitchell.pdf",
            "url": "https://cdn.chools.in/DIG_LIB/E-Book/M1-Machine-Learning-Tom-Mitchell_.pdf",
        },
    ],
    "Data Scientist": [
        {
            "name": "machine_learning_tom_mitchell.pdf",
            "url": "https://cdn.chools.in/DIG_LIB/E-Book/M1-Machine-Learning-Tom-Mitchell_.pdf",
        },
    ],
}

ROLES = ["AI/ML Engineer", "Backend Engineer", "Data Scientist"]

# Difficulty progression
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

# Interview state machine steps
INTERVIEW_STEPS = [
    "warmup",         # 1-2 easy questions
    "core",           # 3-4 medium questions on resume skills
    "deep_dive",      # 2-3 hard questions on weak areas
    "scenario",       # 1-2 applied scenario questions
    "closing",        # done
]
