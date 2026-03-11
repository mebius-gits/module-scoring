"""
AST Converter：將新的 ScoringYamlSchema 轉換為舊版 Blockly 相容的 JSON AST 格式。
"""
from typing import Any, Dict

from app.schema.scoring import ScoringYamlSchema


class AstConverter:
    @staticmethod
    def yaml_schema_to_ast(schema: ScoringYamlSchema) -> Dict[str, Any]:
        """
        將 ScoringYamlSchema 轉換為 blocky-ai 期待的 JSON AST 格式。
        目前預設將所有模組合併為單一 AST (Type 3: score_with_formula)
        """
        ast = {
            "score_name": schema.score_name,
            "variables": {},
            "formulas": {},
            "rules": [],
            "risk_levels": []
        }

        # 1. 處理所有模組的 variables, formulas, rules
        for module in schema.modules:
            # 變數
            for var_name, var_def in module.variables.items():
                ast["variables"][var_name] = {
                    "type": var_def.type,
                    "description": var_def.description,
                }

            # 公式
            for formula in module.formulas:
                if formula.formula:
                    # Type 1: 直接公式
                    ast["formulas"][formula.name] = formula.formula
                elif formula.conditions:
                    # Type 2: 結構化條件公式
                    cond_list = []
                    for c in formula.conditions:
                        if c.is_else or not c.condition:
                            cond_list.append({
                                "is_else": True,
                                "value": float(c.value) if isinstance(c.value, str) and c.value.replace('.', '', 1).isdigit() else c.value
                            })
                        else:
                            cond_list.append({
                                "condition": AstConverter._parse_condition_str(c.condition),
                                "value": float(c.value) if isinstance(c.value, str) and c.value.replace('.', '', 1).isdigit() else c.value
                            })
                    
                    ast["formulas"][formula.name] = {
                        "type": "conditional",
                        "conditions": cond_list
                    }

            # 規則
            for rule in module.rules:
                # 轉成 Blockly 的 if -> action 結構
                rule_item = {
                    "condition": AstConverter._parse_condition_str(rule.condition),
                    "action": {
                        "type": "add",
                        "value": float(rule.add) if isinstance(rule.add, (int, float, str)) and str(rule.add).replace('.','',1).isdigit() else 0
                    }
                }
                # 如果是公式關聯，可能需要額外處理
                ast["rules"].append(rule_item)

        # 2. 處理 Risk Levels
        for risk in schema.risk_levels:
            if risk.is_else or not risk.condition:
                # else fallback usually uses a very low threshold in blocky-ai
                cond = {
                    "op": ">=",
                    "left": "score",
                    "right": -9999
                }
            else:
                cond = AstConverter._parse_condition_str(risk.condition)
                if not cond:
                     # fallback
                     cond = {"op": ">=", "left": "score", "right": -9999}
                     
            ast["risk_levels"].append({
                "condition": cond,
                "text": risk.text
            })

        return ast

    @staticmethod
    def _parse_condition_str(cond_str: str) -> Dict[str, Any]:
        """簡易版 condition string parser，仿造 parser_ai.py 的 parse_condition_str"""
        import re
        cond_str = cond_str.strip()
        
        # 簡單處理 compound
        if ' and ' in cond_str:
            parts = cond_str.split(' and ')
            return {
                "compound": "and",
                "conditions": [AstConverter._parse_condition_str(p) for p in parts]
            }
        if ' or ' in cond_str:
            parts = cond_str.split(' or ')
            return {
                "compound": "or",
                "conditions": [AstConverter._parse_condition_str(p) for p in parts]
            }
            
        # 移除括號
        if cond_str.startswith('(') and cond_str.endswith(')'):
            cond_str = cond_str[1:-1].strip()
            
        pattern = r'^(\w+)\s*(>=|<=|==|>|<|!=|is\s+not|is)\s*(.+)$'
        match = re.match(pattern, cond_str, re.IGNORECASE)
        if match:
            left = match.group(1)
            op = match.group(2).strip().lower()
            right_str = match.group(3).strip()
            
            if op == 'is': op = '=='
            elif op == 'is not': op = '!='
            
            if right_str.lower() == 'true': right = True
            elif right_str.lower() == 'false': right = False
            else:
                try:
                    right = float(right_str)
                    if right == int(right): right = int(right)
                except:
                    right = right_str
            return {"op": op, "left": left, "right": right}
            
        if cond_str.isidentifier():
            return {"op": "==", "left": cond_str, "right": True}
            
        return {}
