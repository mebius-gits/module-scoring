"""Generate and revise scoring YAML through Gemini."""
from typing import List, Optional, Tuple

from app.infra.clients.gemini_client import GeminiClient
from app.services.ai.prompts import build_chat_prompt, build_generate_prompt


class FormulaGenerator:
    """Facade over Gemini for formula generation and mixed chat."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    def generate_formula_yaml(self, description: str) -> str:
        """Generate YAML from a natural-language description."""
        system_prompt = build_generate_prompt()
        prompt = f"{system_prompt}\n\nGenerate modular YAML for:\n{description}"
        raw_output = self.gemini_client.generate_content(prompt)
        return self._clean_yaml_output(raw_output)

    def chat(
        self,
        message: str,
        patient_fields: Optional[List[dict]] = None,
        attachments: Optional[List[dict]] = None,
        conversation_history: Optional[List[dict]] = None,
        current_yaml: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Handle mixed-mode chat with optional memory and YAML revision input."""
        prompt = build_chat_prompt(
            user_message=message,
            conversation_history=self._build_conversation_history_hint(
                conversation_history
            ),
            current_yaml=self._build_current_yaml_hint(current_yaml),
            patient_fields_hint=self._build_patient_fields_hint(patient_fields),
            attachments_hint=self._build_attachments_hint(attachments),
        )
        full_text = self.gemini_client.generate_content(prompt).strip()
        return self._parse_chat_response(full_text)

    def _parse_chat_response(
        self, full_text: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse reply, description, and YAML blocks from model output."""
        has_formula = "FORMULA_START" in full_text and "FORMULA_END" in full_text
        has_desc = (
            "DESCRIPTION_START" in full_text and "DESCRIPTION_END" in full_text
        )

        if not has_formula:
            return full_text, None, None

        yaml_raw = full_text[
            full_text.index("FORMULA_START") + len("FORMULA_START") :
            full_text.index("FORMULA_END")
        ].strip()
        yaml_content = self._clean_yaml_output(yaml_raw)

        formula_description = None
        if has_desc:
            formula_description = full_text[
                full_text.index("DESCRIPTION_START")
                + len("DESCRIPTION_START") : full_text.index("DESCRIPTION_END")
            ].strip()

        reply_text = full_text
        if has_desc:
            reply_text = (
                reply_text[: reply_text.index("DESCRIPTION_START")]
                + reply_text[
                    reply_text.index("DESCRIPTION_END") + len("DESCRIPTION_END") :
                ]
            )
        reply_text = (
            reply_text[: reply_text.index("FORMULA_START")]
            + reply_text[reply_text.index("FORMULA_END") + len("FORMULA_END") :]
        ).strip()

        if not reply_text:
            reply_text = "已根據需求產生或修改 YAML。"

        return reply_text, formula_description, yaml_content

    @staticmethod
    def _build_patient_fields_hint(patient_fields: Optional[List[dict]]) -> str:
        if not patient_fields:
            return ""
        fields_list = ", ".join(
            f"{f['field_name']} ({f['label']})" if f.get("label") else f["field_name"]
            for f in patient_fields
        )
        return (
            "AVAILABLE PATIENT FIELDS (prefer these variable names): "
            f"{fields_list}\n"
            "Use the exact field_name as the variable name in formulas."
        )

    @staticmethod
    def _build_attachments_hint(attachments: Optional[List[dict]]) -> str:
        if not attachments:
            return ""
        file_parts = [
            f"--- FILE: {att['filename']} ---\n{att['content']}\n--- END FILE ---"
            for att in attachments
        ]
        return "ATTACHED FILES:\n" + "\n".join(file_parts)

    @staticmethod
    def _build_conversation_history_hint(
        conversation_history: Optional[List[dict]],
    ) -> str:
        if not conversation_history:
            return ""

        lines = [
            "CONVERSATION HISTORY (oldest to newest):",
            "Use this as memory, but prioritize the latest user request.",
        ]
        for item in conversation_history:
            role = str(item.get("role", "assistant")).upper()
            content = (item.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
            formula_description = (item.get("formula_description") or "").strip()
            if formula_description:
                lines.append(f"{role} DESCRIPTION:\n{formula_description}")
            generated_yaml = (item.get("generated_yaml") or "").strip()
            if generated_yaml:
                lines.append(f"{role} GENERATED YAML:\n{generated_yaml}")
        return "\n".join(lines)

    @staticmethod
    def _build_current_yaml_hint(current_yaml: Optional[str]) -> str:
        if not current_yaml:
            return ""
        return (
            "CURRENT YAML TO MODIFY:\n"
            "If the user asks for changes, revise this YAML and return the full "
            "updated YAML.\n"
            f"{current_yaml}"
        )

    @staticmethod
    def _clean_yaml_output(raw: str) -> str:
        """Strip markdown code fences from model output."""
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
