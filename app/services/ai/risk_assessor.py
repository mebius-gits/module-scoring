"""
Risk Assessor Skill：根據全局分數對應風險等級文字。
"""
from typing import List

from app.models.scoring import RiskLevelDefinition


class RiskAssessor:
    """Risk Assessor Skill：將全局 score 對應到 risk_level"""

    @staticmethod
    def assess_risk(score: float, risk_levels: List[RiskLevelDefinition]) -> str:
        """
        根據全局 score 對應風險等級。

        Args:
            score: 全局分數
            risk_levels: 風險等級定義列表
        Returns:
            對應的風險等級文字
        """
        for level in risk_levels:
            if level.is_else:
                return level.text

            if level.condition:
                # 將 'score' 替換為實際值後評估
                condition = level.condition.strip()
                try:
                    result = RiskAssessor._evaluate_score_condition(
                        condition, score
                    )
                    if result:
                        return level.text
                except Exception:
                    continue

        return "Unknown Risk Level"

    @staticmethod
    def _evaluate_score_condition(condition: str, score: float) -> bool:
        """
        評估 score 條件表達式。

        支援格式: 'score >= 12', 'score >= 6'
        """
        import operator

        operators = {
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            "==": operator.eq,
            "!=": operator.ne,
        }

        for op_str, op_func in operators.items():
            if op_str in condition:
                _, right = condition.split(op_str, 1)
                right_val = float(right.strip())
                return op_func(score, right_val)

        return False
