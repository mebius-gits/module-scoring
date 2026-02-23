"""
Gemini Client：封裝 google-genai SDK，提供簡單介面供 Service 層呼叫。
安裝：pip install -U google-genai
"""
from google import genai
from app.infra.settings import settings


class GeminiClient:
    """封裝 Google GenAI SDK，統一管理 API 金鑰與 Model 設定"""

    def __init__(self):
        # 若 GOOGLE_API_KEY 為空，SDK 會自動使用環境變數 GEMINI_API_KEY
        api_key = settings.GOOGLE_API_KEY or None
        self.client = genai.Client(api_key=api_key)
        self.model = settings.GEMINI_MODEL

    def generate_content(self, prompt: str) -> str:
        """
        呼叫 Gemini 生成文字回應。

        Args:
            prompt: 組好的 Prompt 字串
        Returns:
            Gemini 回傳的文字內容
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    def summarize_items(self, items_text: str) -> str:
        """
        Items 列表摘要技能 (Skill)。
        由 TaskService 組裝後呼叫，封裝 Prompt 細節。

        Args:
            items_text: 以逗號分隔的商品名稱列表
        Returns:
            Gemini 摘要文字
        """
        prompt = (
            "你是一位商品分析助手。請依照以下商品列表，"
            "提供一段不超過 100 字的繁體中文摘要，說明品項組成與特點：\n"
            f"{items_text}"
        )
        return self.generate_content(prompt)
