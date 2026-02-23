"""
Settings 模組：使用 pydantic-settings 管理所有環境變數。
修改環境變數請在 .env 檔案或作業系統環境中設定，無需修改程式碼。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 資料庫 ──────────────────────────────────────────
    # 支援 SQLite / PostgreSQL / MySQL，以 URL scheme 區分
    # 範例：postgresql://user:pass@localhost/db
    #        mysql+pymysql://user:pass@localhost/db
    DB_URL: str = "sqlite:///./app.db"

    # ── Google Gemini ────────────────────────────────────
    # 以 GOOGLE_API_KEY 為主，若為空則 SDK 自動讀取環境變數 GEMINI_API_KEY
    GOOGLE_API_KEY: str = ""
    # Gemini 模型名稱，可在 .env 中覆寫
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── AI API 認證 ──────────────────────────────────────
    # /ai/v1 路由需在 Request Header X-AI-KEY 傳入此值
    AI_HEADER_KEY: str = "changeme"

    # ── 速率限制 (Rate Limit Stub) ───────────────────────
    AI_RATE_LIMIT_PER_KEY: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
