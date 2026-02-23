"""
Scoring Repository：In-memory 公式儲存庫。
負責 CRUD 操作，未來可替換為 SQLAlchemy 實作。
"""
import uuid
from typing import Any, Dict, List, Optional

from app.common.exceptions import NotFoundException
from app.models.scoring import FormulaStorageItem


# 全局 store，模擬 DB persistence
_FORMULA_STORE: Dict[str, dict] = {}


class ScoringRepo:
    """
    In-memory Scoring Repository 實作。
    Repository 介面明確，未來可無縫替換為 DB 版本。
    """

    def save_formula(
        self,
        yaml_content: str,
        score_name: str,
        module_count: int,
        ast_data: Optional[Dict[str, Any]] = None,
    ) -> FormulaStorageItem:
        """儲存公式，自動產生 ID"""
        formula_id = str(uuid.uuid4())
        item = FormulaStorageItem(
            formula_id=formula_id,
            score_name=score_name,
            yaml_content=yaml_content,
            ast_data=ast_data,
            module_count=module_count,
        )
        _FORMULA_STORE[formula_id] = item.model_dump()
        return item

    def clear_all(self) -> None:
        """清空所有公式（測試用）"""
        _FORMULA_STORE.clear()
