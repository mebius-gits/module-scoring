"""
Formula Generator Skill：透過 Gemini AI 根據文字描述生成結構化 YAML 公式。
支援智慧分模組：AI 根據公式複雜度與變數共享自動將公式分組為不同模組。
支援混合模式聊天：AI 根據使用者訊息自動判斷是一般對話或公式生成請求。
"""
from typing import List, Optional, Tuple

from app.infra.clients.gemini_client import GeminiClient


# ── System Prompt：指示 AI 生成分模組 YAML ────────────────────────
_SYSTEM_PROMPT = """You are a specialized medical/clinical scoring formula generator AI.
Your task is to generate modular YAML scoring definitions that follow a strict structure.

CRITICAL RULES FOR MODULE SPLITTING:
1. If formula count >= 5 OR formulas contain complex conditions (multi-layer if/else, and/or), you MUST split into modules.
2. Module names should clearly describe the formula concept, examples:
   - Demographics (age, gender related)
   - RenalFunction (kidney, creatinine, clearance)
   - CardiacMarkers (troponin, ECG, heart)
   - HistoryRisk (medical history, risk factors)
   - LabTest (laboratory values)
   - VitalSigns (blood pressure, heart rate)
3. Group formulas by their clinical/logical domain.
4. Variables shared across modules should be declared in each module that uses them.

MODULE CONTENT STRUCTURE:
Each module must contain:
  - name: module name (PascalCase)
  - variables: variable name to type mapping (int, float, boolean)
  - formulas: list of formula definitions
  - rules: MANDATORY scoring adjustments based on formula results

FORMULA TYPES SUPPORTED:
  Type 1 - Direct formula expression:
    - name: male_base_clearance
      formula: ((140 - age) * weight) / (72 * serum_creatinine)

  Type 2 - Conditional formula (if/else):
    - name: age_factor
      conditions:
        - if: age > 80
          value: 3
        - if: age > 60
          value: 2
        - else:
          value: 1

CONDITION EXPRESSIONS SUPPORTED:
  - Comparison: >, <, >=, <=, ==, !=
  - Logical: and, or, not
  - Boolean variables: is_female (evaluates to true/false)
  - Compound: serum_creatinine > 2 and weight < 50

FORMULA CROSS-REFERENCES:
  - Formulas within a module CAN reference previous formula names in the same module.
  - Formulas CAN reference formula names from earlier modules.
  - Example: adjusted_clearance formula can reference male_base_clearance.

RULES (MANDATORY - EVERY module MUST have rules):
  - Rules define how formula results contribute to the global score.
  - Without rules, formulas are calculated but do NOT contribute to the score.
  - Format: if: <condition referencing a formula name>, add: <numeric_value>
  - Rules are evaluated after all formulas in the module are calculated.
  - EVERY scoring formula MUST have at least one corresponding rule.
  - Example rules for conditional formulas:
    rules:
      - if: age_score >= 2
        add: 2
      - if: gender_score >= 1
        add: 1
  - For direct expression formulas, use threshold-based rules:
    rules:
      - if: bmi_value >= 30
        add: 4
      - if: bmi_value >= 25
        add: 2

RISK LEVELS:
  - Must cover ALL possible score ranges.
  - Must include an else clause as the final entry.
  - Conditions evaluated from top to bottom, first match wins.

STRICT OUTPUT FORMAT:
score_name: <ScoreName_In_Snake_Case>

modules:
  - name: <ModuleName>
    variables:
      <variable_name>: <type>
    formulas:
      - name: <formula_name>
        formula: <math_expression>
      - name: <formula_name>
        conditions:
          - if: <condition>
            value: <numeric_value>
          - else:
            value: <numeric_value>
    rules:
      - if: <condition>
        add: <numeric_value>

risk_levels:
  - if: score >= <threshold>
    text: <risk description>
  - if: score >= <threshold>
    text: <risk description>
  - else:
    text: <risk description>

ABSOLUTE RULES:
1. Output ONLY valid YAML. No markdown fences, no explanations, no emoji.
2. DO NOT output any comments (# 註解) in the YAML.
3. DO NOT use double quotes ("") around formula expressions or text strings.
4. DO NOT generate 'description' fields anywhere in the output.
5. Use snake_case for all variable and formula names.
6. Use PascalCase for module names.
7. Variable types must be: int, float, or boolean.
8. risk_levels must cover all score ranges including an else clause.
9. All numeric values must be actual numbers, not strings.
10. Formula expressions must use variable names and standard arithmetic (+, -, *, /, parentheses).
11. NEVER use inline if/else or ternary expressions inside a formula field. Formula fields MUST contain ONLY pure math expressions (variables, numbers, +, -, *, /, parentheses). ANY conditional logic (if/else) MUST use the conditions block format instead.
    WRONG: formula: base_clearance * (1 if is_female else 0.85)
    CORRECT: Use a separate conditions-based formula for the conditional part, then reference it.
12. If a formula needs to incorporate a conditional value, create a separate conditions-based formula first, then reference its name in the math expression.
    Example: First define gender_factor with conditions (if: is_female -> 0.85, else -> 1), then use formula: base_clearance * gender_factor.
"""


class FormulaGenerator:
    """Formula Generator Skill：呼叫 Gemini AI 生成分模組 YAML 公式"""

    # ── 混合模式 Chat Prompt ─────────────────────────────────────
    _CHAT_PROMPT_TEMPLATE = """You are a helpful medical formula assistant. You can have general conversations AND generate medical scoring formulas.

DECIDE based on the user's message:
- If the user is asking a QUESTION, making SMALL TALK, requesting EXPLANATION, or saying something non-formula → reply conversationally in Traditional Chinese (繁體中文). Do NOT generate a formula.
- If the user is REQUESTING A FORMULA or scoring system → reply conversationally AND include the formula using the markers below.

User's message: {user_message}
{patient_fields_hint}

IF generating a formula, embed it exactly between these markers (markers on their own lines):
FORMULA_START
<your YAML formula following the strict structure below>
FORMULA_END

The YAML inside the markers MUST follow this exact structure:

score_name: <ScoreName>

modules:
  - name: <ModuleName>
    variables:
      <variable_name>: <type>
    formulas:
      - name: <formula_name>
        formula: <math_expression>
      OR
      - name: <formula_name>
        conditions:
          - if: <condition>
            value: <numeric_value>
          - else:
            value: <numeric_value>
    rules:
      - if: <condition>
        add: <numeric_value>

risk_levels:
  - if: score >= <threshold>
    text: <risk description>
  - else:
    text: <low risk description>

YAML GENERATION RULES (only when generating):
1. Use snake_case for all variable and formula names.
2. Use PascalCase for module names.
3. Variable types must be: int, float, or boolean.
4. Every module MUST have at least one rule.
5. risk_levels must cover all score ranges including an else clause.
6. DO NOT output any comments (# lines) in the YAML.
7. DO NOT use double quotes around formula expressions or text strings.
8. DO NOT generate 'description' fields in the YAML.
9. All numeric values must be actual numbers, not strings.
10. If formula count >= 5, split into multiple modules by clinical domain.
11. Conditions may use: >, <, >=, <=, ==, !=, and, or, not.
12. NEVER use inline if/else or ternary expressions inside a formula field. Formula fields MUST contain ONLY pure math (variables, numbers, +, -, *, /, parentheses). ALL conditional logic MUST use the conditions block format.
    WRONG: formula: base * (1 if is_female else 0.85)
    CORRECT: Create a conditions-based formula for the conditional part, then reference its name in the math formula.

Your conversational reply must be in 繁體中文 (Traditional Chinese)."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    def generate_formula_yaml(self, description: str) -> str:
        """
        根據描述文字呼叫 Gemini 生成分模組 YAML 公式。

        Args:
            description: 模組/評分系統的文字描述
        Returns:
            生成的 YAML 字串
        """
        prompt = f"{_SYSTEM_PROMPT}\n\nGenerate modular YAML for:\n{description}"
        raw_output = self.gemini_client.generate_content(prompt)

        # 清理 AI 回傳：移除可能的 markdown 標記
        cleaned = self._clean_yaml_output(raw_output)
        return cleaned

    def chat(
        self,
        message: str,
        patient_fields: Optional[List[dict]] = None,
        attachments: Optional[List[dict]] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        混合模式聊天：AI 自動判斷是一般對話或公式生成請求。
        當判斷為公式生成時，回傳 YAML 公式；否則僅回傳對話文字。

        Args:
            message: 使用者訊息
            patient_fields: 病人欄位清單 [{"field_name": "age", "label": "年齡 (歲)", "field_type": "int"}, ...]
            attachments: 使用者附加的檔案 [{"filename": "...", "content": "..."}]
        Returns:
            Tuple[str, Optional[str]]: (對話回覆, YAML 公式字串 or None)
        """
        # 組裝 patient fields hint
        if patient_fields:
            fields_list = ", ".join(
                f"{f['field_name']} ({f['label']})" if f.get("label") else f["field_name"]
                for f in patient_fields
            )
            patient_fields_hint = (
                f"\n\nAVAILABLE PATIENT FIELDS with units (use these variable names preferentially): {fields_list}\n"
                f"Use the exact field_name as the variable name in formulas. The label shows the unit."
            )
        else:
            patient_fields_hint = ""

        # 組裝 file attachments hint
        attachments_hint = ""
        if attachments:
            file_parts = []
            for att in attachments:
                file_parts.append(
                    f"--- FILE: {att['filename']} ---\n{att['content']}\n--- END FILE ---"
                )
            attachments_hint = (
                "\n\nATTACHED FILES (user uploaded for reference):\n"
                + "\n".join(file_parts)
            )

        prompt = self._CHAT_PROMPT_TEMPLATE.format(
            user_message=message,
            patient_fields_hint=patient_fields_hint,
        ) + attachments_hint
        full_text = self.gemini_client.generate_content(prompt).strip()

        # 解析：分離對話回覆與公式區塊
        if "FORMULA_START" in full_text and "FORMULA_END" in full_text:
            before = full_text[: full_text.index("FORMULA_START")].strip()
            formula_raw = full_text[
                full_text.index("FORMULA_START") + len("FORMULA_START"):
                full_text.index("FORMULA_END")
            ].strip()
            after = full_text[full_text.index("FORMULA_END") + len("FORMULA_END"):].strip()

            # 清理 markdown fences
            yaml_content = self._clean_yaml_output(formula_raw)

            reply_parts = [p for p in [before, after] if p]
            reply_text = "\n".join(reply_parts) if reply_parts else "公式已生成，請使用回傳資料進行後續操作。"

            return reply_text, yaml_content
        else:
            return full_text, None



    @staticmethod
    def _clean_yaml_output(raw: str) -> str:
        """
        清理 AI 回傳的 YAML。
        移除 ```yaml ... ``` 等 markdown 包裝。
        """
        lines = raw.strip().split("\n")
        result = []
        in_fence = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                result.append(line)

        return "\n".join(result).strip()
