"""
Formula Generator Skill：透過 Gemini AI 根據文字描述生成結構化 YAML 公式。
Prompt 邏輯已抽離至 prompts.py，本模組僅負責呼叫與解析。
"""
from typing import List, Optional, Tuple

from app.infra.clients.gemini_client import GeminiClient
from app.services.ai.prompts import build_generate_prompt, build_chat_prompt


class FormulaGenerator:
    """Formula Generator Skill：呼叫 Gemini AI 生成分模組 YAML 公式"""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    # ── 純生成模式 ───────────────────────────────────────────────

    def generate_formula_yaml(self, description: str) -> str:
        """
        根據描述文字呼叫 Gemini 生成分模組 YAML 公式。

        Args:
            description: 模組/評分系統的文字描述
        Returns:
            生成的 YAML 字串
        """
        system_prompt = build_generate_prompt()
        prompt = f"{system_prompt}\n\nGenerate modular YAML for:\n{description}"
        raw_output = self.gemini_client.generate_content(prompt)
        return self._clean_yaml_output(raw_output)

    # ── 混合聊天模式 ─────────────────────────────────────────────

    def chat(
        self,
        message: str,
        patient_fields: Optional[List[dict]] = None,
        attachments: Optional[List[dict]] = None,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        混合模式聊天：AI 自動判斷是一般對話或公式生成請求。

        Returns:
            Tuple[reply, formula_description, yaml_content]:
              - reply: 對話回覆（繁體中文，永遠有值）
              - formula_description: 公式臨床描述（僅公式生成時有值）
              - yaml_content: YAML 公式字串（僅公式生成時有值）
        """
        patient_fields_hint = self._build_patient_fields_hint(patient_fields)
        attachments_hint = self._build_attachments_hint(attachments)

        prompt = build_chat_prompt(
            user_message=message,
            patient_fields_hint=patient_fields_hint,
            attachments_hint=attachments_hint,
        )
        full_text = self.gemini_client.generate_content(prompt).strip()

        return self._parse_chat_response(full_text)

    # ── 解析 AI 回應 ─────────────────────────────────────────────

    def _parse_chat_response(
        self, full_text: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        從 AI 原始回應中分離：reply / formula_description / yaml_content。
        """
        has_formula = "FORMULA_START" in full_text and "FORMULA_END" in full_text
        has_desc = "DESCRIPTION_START" in full_text and "DESCRIPTION_END" in full_text

        if not has_formula:
            return full_text, None, None

        # 取出 YAML
        yaml_raw = full_text[
            full_text.index("FORMULA_START") + len("FORMULA_START"):
            full_text.index("FORMULA_END")
        ].strip()
        yaml_content = self._clean_yaml_output(yaml_raw)

        # 取出 description
        formula_description = None
        if has_desc:
            formula_description = full_text[
                full_text.index("DESCRIPTION_START") + len("DESCRIPTION_START"):
                full_text.index("DESCRIPTION_END")
            ].strip()

        # 取出 reply（移除標記區塊後的剩餘文字）
        reply_text = full_text
        # 移除 DESCRIPTION 區塊
        if has_desc:
            reply_text = (
                reply_text[:reply_text.index("DESCRIPTION_START")]
                + reply_text[reply_text.index("DESCRIPTION_END") + len("DESCRIPTION_END"):]
            )
        # 移除 FORMULA 區塊
        reply_text = (
            reply_text[:reply_text.index("FORMULA_START")]
            + reply_text[reply_text.index("FORMULA_END") + len("FORMULA_END"):]
        )
        reply_text = reply_text.strip()

        if not reply_text:
            reply_text = "公式已生成，請查看下方描述與 YAML 內容。"

        return reply_text, formula_description, yaml_content

    # ── Hint 組裝 ────────────────────────────────────────────────

    @staticmethod
    def _build_patient_fields_hint(patient_fields: Optional[List[dict]]) -> str:
        if not patient_fields:
            return ""
        fields_list = ", ".join(
            f"{f['field_name']} ({f['label']})" if f.get("label") else f["field_name"]
            for f in patient_fields
        )
        return (
            f"\nAVAILABLE PATIENT FIELDS with units (use these variable names preferentially): {fields_list}\n"
            f"Use the exact field_name as the variable name in formulas. The label shows the unit."
        )

    @staticmethod
    def _build_attachments_hint(attachments: Optional[List[dict]]) -> str:
        if not attachments:
            return ""
        file_parts = [
            f"--- FILE: {att['filename']} ---\n{att['content']}\n--- END FILE ---"
            for att in attachments
        ]
        return "\nATTACHED FILES (user uploaded for reference):\n" + "\n".join(file_parts)

    # ── YAML 清理 ────────────────────────────────────────────────

    @staticmethod
    def _clean_yaml_output(raw: str) -> str:
        """移除 ```yaml ... ``` 等 markdown 包裝。"""
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
