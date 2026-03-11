"""
Score Calculator Skill：核心計算引擎。
負責解析條件表達式、計算公式值、套用規則、累加全局分數。
支援：比較運算、and/or 邏輯、公式互相引用、數學表達式。
"""
import operator
import re
from typing import Any, Dict, List, Tuple

from app.schema.scoring import (
    ConditionBlock,
    FormulaDefinition,
    ModuleDefinition,
    ModuleScoreResult,
    ScoringYamlSchema,
)


# ── 支援的比較運算子 ──────────────────────────────────────────────
_OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}


class ScoreCalculator:
    """
    Score Calculator Skill：計算模組分數與全局分數。
    遵循 Clean Architecture，不依賴 HTTP，只接收結構化輸入。
    """

    @staticmethod
    def evaluate_condition(condition_str: str, context: Dict[str, Any]) -> bool:
        """
        解析並評估條件表達式。

        支援格式:
            - 'age > 80'
            - 'is_female'  (boolean)
            - 'serum_creatinine > 2 and weight < 50'
            - 'troponin_level >= 2 or ecg_score >= 1'

        Args:
            condition_str: 條件字串
            context: 當前計算上下文 (變數 + 已計算的公式值)
        Returns:
            條件是否成立
        """
        condition_str = condition_str.strip()

        # 處理 and 邏輯
        if " and " in condition_str:
            parts = condition_str.split(" and ")
            return all(
                ScoreCalculator.evaluate_condition(p.strip(), context)
                for p in parts
            )

        # 處理 or 邏輯
        if " or " in condition_str:
            parts = condition_str.split(" or ")
            return any(
                ScoreCalculator.evaluate_condition(p.strip(), context)
                for p in parts
            )

        # 處理 not 邏輯
        if condition_str.startswith("not "):
            return not ScoreCalculator.evaluate_condition(
                condition_str[4:].strip(), context
            )

        # 處理比較運算子
        for op_str, op_func in _OPERATORS.items():
            if op_str in condition_str:
                left, right = condition_str.split(op_str, 1)
                left_val = ScoreCalculator._resolve_value(left.strip(), context)
                right_val = ScoreCalculator._resolve_value(right.strip(), context)
                return op_func(float(left_val), float(right_val))

        # 處理純 boolean 變數 (例如 'is_female')
        val = ScoreCalculator._resolve_value(condition_str, context)
        return bool(val)

    @staticmethod
    def evaluate_formula(formula: FormulaDefinition, context: Dict[str, Any]) -> Any:
        """
        評估單一公式，回傳計算結果。

        Args:
            formula: 公式定義
            context: 當前計算上下文
        Returns:
            計算結果 (float 或 str)
        """
        # 條件公式表
        if formula.conditions:
            for cond in formula.conditions:
                if cond.is_else:
                    return ScoreCalculator._resolve_expression(cond.value, context)
                if cond.condition and ScoreCalculator.evaluate_condition(
                    cond.condition, context
                ):
                    return ScoreCalculator._resolve_expression(cond.value, context)
            return 0

        # 直接數學表達式
        if formula.formula:
            return ScoreCalculator._resolve_expression(formula.formula, context)

        return 0

    @staticmethod
    def calculate_module(
        module: ModuleDefinition,
        variables: Dict[str, Any],
        shared_context: Dict[str, Any],
    ) -> ModuleScoreResult:
        """
        計算單一模組的所有公式與規則。

        Args:
            module: 模組定義
            variables: 使用者提供的輸入變數
            shared_context: 跨模組共用的上下文 (供公式互相引用)
        Returns:
            ModuleScoreResult: 模組計算結果
        """
        # 合併變數到 context
        context = {**shared_context, **variables}
        formula_results = {}
        module_score = 0.0
        rules_applied = []

        # 依序計算每個 formula
        for formula in module.formulas:
            result = ScoreCalculator.evaluate_formula(formula, context)
            formula_results[formula.name] = result
            # 將公式結果加入 context，供後續公式引用
            context[formula.name] = result
            # 同步更新 shared_context
            shared_context[formula.name] = result

        # 套用 rules
        if module.rules:
            for rule in module.rules:
                if ScoreCalculator.evaluate_condition(rule.condition, context):
                    # add 可能是數字或變數名引用
                    add_val = rule.add
                    if isinstance(add_val, str):
                        add_val = float(context.get(add_val, 0))
                    module_score += add_val
                    rules_applied.append(
                        f"{rule.condition} -> +{add_val}"
                    )
        else:
            # 若無 rules，自動加總「葉節點」公式結果
            # 排除被其他公式引用的中間計算值 (如 bmi_value)
            referenced = set()
            for f in module.formulas:
                # 檢查 formula expression 和 conditions 中引用了哪些公式名
                texts = []
                if f.formula:
                    texts.append(f.formula)
                for c in (f.conditions or []):
                    if c.condition:
                        texts.append(c.condition)
                for txt in texts:
                    for other in module.formulas:
                        if other.name != f.name and other.name in txt:
                            referenced.add(other.name)

            for name, val in formula_results.items():
                if isinstance(val, (int, float)) and name not in referenced:
                    module_score += val
                    rules_applied.append(
                        f"auto_sum({name}) -> +{val}"
                    )

        return ModuleScoreResult(
            module_name=module.name,
            formula_results=formula_results,
            rules_applied=rules_applied,
            module_score=module_score,
        )

    @staticmethod
    def calculate_all(
        schema: ScoringYamlSchema,
        all_variables: Dict[str, Any],
    ) -> Tuple[Dict[str, ModuleScoreResult], float]:
        """
        計算所有模組並累加全局分數。

        Args:
            schema: YAML Schema
            all_variables: 所有模組共用的輸入變數 (扁平 dict)
        Returns:
            (module_scores dict, global_score float)
        """
        shared_context: Dict[str, Any] = {}
        module_scores: Dict[str, ModuleScoreResult] = {}
        global_score = 0.0

        for module in schema.modules:
            result = ScoreCalculator.calculate_module(
                module, all_variables, shared_context
            )
            module_scores[module.name] = result
            global_score += result.module_score

        return module_scores, global_score

    # ── 內部工具方法 ────────────────────────────────────────────

    @staticmethod
    def _resolve_value(token: str, context: Dict[str, Any]) -> Any:
        """
        解析單一 token 為具體值。
        優先查 context，若為數字則直接轉換。
        """
        token = token.strip()

        # 查 context (變數 / 公式名)
        if token in context:
            return context[token]

        # 嘗試轉換為數字
        try:
            if "." in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        # boolean 字串
        if token.lower() == "true":
            return True
        if token.lower() == "false":
            return False

        return token

    @staticmethod
    def _resolve_expression(expr: Any, context: Dict[str, Any]) -> Any:
        """
        解析數學表達式或直接值。

        支援格式:
            - 數字: 3, 0.85
            - 表達式: 'age_factor * gender_factor'
            - 混合引用: 'male_base_clearance * demo_score'
            - 含常數運算: 'base * 0.75'
        """
        # 如果已經是數字，直接回傳
        if isinstance(expr, (int, float)):
            return expr

        if not isinstance(expr, str):
            return expr

        expr = expr.strip()

        # 純數字字串
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # 替換變數名為實際值，僅替換完整單字
        resolved = expr
        # 找出所有可能的變數名 (字母開頭，可含底線與數字)
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", resolved)
        for token in tokens:
            if token in context:
                val = context[token]
                if isinstance(val, bool):
                    val = 1 if val else 0
                # 使用 word boundary 確保只替換完整的變數名
                resolved = re.sub(rf"\b{re.escape(token)}\b", str(val), resolved)

        # 安全計算數學表達式
        try:
            result = ScoreCalculator._safe_eval(resolved)
            return result
        except Exception:
            return resolved

    @staticmethod
    def _safe_eval(expression: str) -> float:
        """
        安全的數學表達式計算器。
        支援：數字、四則運算、括號、負數。
        例如: ((140 - 85) * 60) / (72 * 1.2)
        """
        # 僅允許安全字元（含負號）
        allowed = set("0123456789.+-*/() ")
        if not all(c in allowed for c in expression):
            raise ValueError(f"不安全的表達式: {expression}")

        # 防止空表達式
        if not expression.strip():
            raise ValueError("空表達式")

        # 使用 eval 搭配空的命名空間以確保安全性
        result = eval(expression, {"__builtins__": {}}, {})
        return float(result)
