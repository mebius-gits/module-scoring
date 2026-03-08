"""
YAML Parser Engine：解析 YAML 字串並驗證為 ScoringYamlSchema。
負責將原始 YAML 文字轉換為結構化的 Pydantic Model。
"""
import yaml

from app.common.exceptions import ValidationException
from app.models.scoring import (
    ConditionBlock,
    FormulaDefinition,
    ModuleDefinition,
    RiskLevelDefinition,
    RuleDefinition,
    ScoringYamlSchema,
    VariableDefinition,
)


class YamlParser:
    """YAML 解析器：將 YAML 字串解析為 ScoringYamlSchema"""

    @staticmethod
    def parse_yaml(yaml_string: str) -> ScoringYamlSchema:
        """
        解析 YAML 字串為 ScoringYamlSchema。

        Args:
            yaml_string: 原始 YAML 文字
        Returns:
            ScoringYamlSchema 物件
        Raises:
            ValidationException: YAML 格式不正確或結構不符合規範
        """
        try:
            raw = yaml.safe_load(yaml_string)
        except yaml.YAMLError as e:
            raise ValidationException(f"YAML 語法錯誤: {e}")

        if not isinstance(raw, dict):
            raise ValidationException("YAML 頂層必須是 dict 結構")

        score_name = raw.get("score_name") or raw.get("scorename") or raw.get("score", "Unnamed Score")
        raw["score_name"] = score_name

        try:
            schema = YamlParser._build_schema(raw)
        except Exception as e:
            raise ValidationException(f"YAML 結構解析失敗: {e}")

        # 驗證交叉引用
        errors = YamlParser.validate_schema(schema)
        if errors:
            raise ValidationException(f"YAML 驗證失敗: {'; '.join(errors)}")

        return schema

    @staticmethod
    def _build_schema(raw: dict) -> ScoringYamlSchema:
        """從 raw dict 建構 ScoringYamlSchema"""
        modules = []
        
        raw_modules = raw.get("modules", [])
        if isinstance(raw_modules, dict):
            # 兼容 AI 將 module 生成為 dict 的情況: { "History": { "variables": ... }, "ECG": {...} }
            raw_modules_list = []
            for k, v in raw_modules.items():
                if isinstance(v, dict):
                    v["name"] = k
                    raw_modules_list.append(v)
            raw_modules = raw_modules_list

        for mod_raw in raw_modules:
            formulas = []
            for f_raw in mod_raw.get("formulas", []):
                conditions = None
                if "conditions" in f_raw and f_raw["conditions"]:
                    conditions = YamlParser._parse_conditions(f_raw["conditions"])

                formulas.append(FormulaDefinition(
                    name=f_raw["name"],
                    description=f_raw.get("description", ""),
                    conditions=conditions,
                    formula=f_raw.get("formula"),
                ))

            rules = []
            for r_raw in mod_raw.get("rules", []):
                raw_cond = r_raw.get("if", r_raw.get("condition", ""))
                if isinstance(raw_cond, bool):
                    raw_cond = str(raw_cond).lower()
                rules.append(RuleDefinition(
                    condition=str(raw_cond) if raw_cond is not None else "",
                    add=r_raw.get("add", 0),
                ))

            # variables: 支援多種格式
            # 1. Dict[str, str]: {name: type}  (向後相容)
            # 2. Dict[str, dict]: {name: {type: ..., description: ...}}
            # 3. List: [name, ...]
            raw_variables = mod_raw.get("variables", {})
            variables = {}
            if isinstance(raw_variables, list):
                variables = {str(v): VariableDefinition(type="any") for v in raw_variables}
            elif isinstance(raw_variables, dict):
                for var_name, var_val in raw_variables.items():
                    if isinstance(var_val, str):
                        variables[var_name] = VariableDefinition(type=var_val)
                    elif isinstance(var_val, dict):
                        variables[var_name] = VariableDefinition(
                            type=var_val.get("type", "any"),
                            description=var_val.get("description", ""),
                        )
                    else:
                        variables[str(var_name)] = VariableDefinition(type="any")

            modules.append(ModuleDefinition(
                name=mod_raw.get("name") or mod_raw.get("module_name", "Unnamed"),
                variables=variables,
                formulas=formulas,
                rules=rules,
            ))

        risk_levels = []
        for rl_raw in raw.get("risk_levels", []):
            is_else = "else" in rl_raw
            condition = rl_raw.get("if", rl_raw.get("condition"))
            if isinstance(condition, bool):
                condition = str(condition).lower()
            elif condition is not None:
                condition = str(condition)
            risk_levels.append(RiskLevelDefinition(
                condition=condition,
                is_else=is_else,
                text=rl_raw.get("text", ""),
            ))

        return ScoringYamlSchema(
            score_name=raw["score_name"],
            modules=modules,
            risk_levels=risk_levels,
        )

    @staticmethod
    def _parse_conditions(conditions_raw: list) -> list[ConditionBlock]:
        """解析條件列表"""
        result = []
        for c in conditions_raw:
            is_else = "else" in c
            condition = c.get("if", c.get("condition"))
            if isinstance(condition, bool):
                condition = str(condition).lower()
            elif condition is not None:
                condition = str(condition)
            value = c.get("value", 0)
            result.append(ConditionBlock(
                condition=condition,
                is_else=is_else,
                value=value,
            ))
        return result

    @staticmethod
    def validate_schema(schema: ScoringYamlSchema) -> list[str]:
        """
        驗證 Schema 的交叉引用完整性。

        Returns:
            錯誤訊息列表，空列表表示驗證通過
        """
        errors = []

        if not schema.score_name:
            errors.append("score_name 不可為空")

        if not schema.modules:
            errors.append("至少需要一個 module")

        for module in schema.modules:
            if not module.name:
                errors.append("module name 不可為空")

            if not module.formulas:
                errors.append(f"Module '{module.name}' 至少需要一個 formula")

            # 檢查公式名稱唯一性
            formula_names = [f.name for f in module.formulas]
            duplicates = [n for n in formula_names if formula_names.count(n) > 1]
            if duplicates:
                errors.append(
                    f"Module '{module.name}' 有重複的公式名稱: {set(duplicates)}"
                )

        return errors
