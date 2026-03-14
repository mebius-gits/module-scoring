"""Application service for AI chat, YAML parsing, and score calculation."""
from typing import Any, Dict

from app.common.ast_converter import AstConverter
from app.common.exceptions import NotFoundException, ValidationException
from app.infra.clients.gemini_client import GeminiClient
from app.repositories.ai_chat_repo import AiChatMessageRepo, AiChatSessionRepo
from app.repositories.formula_repo import FormulaRepo
from app.repositories.patient_field_repo import PatientFieldRepo
from app.schema.scoring import (
    CalculateScoreRequest,
    ChatResponse,
    ChatV2Response,
    ExtractVariablesRequest,
    ExtractVariablesResponse,
    ScoreResponse,
    VariableInfo,
)
from app.services.ai.formula_generator import FormulaGenerator
from app.services.ai.risk_assessor import RiskAssessor
from app.services.ai.score_calculator import ScoreCalculator
from app.services.ai.yaml_parser import YamlParser


class ScoringService:
    """Orchestrates AI chat, YAML parsing, score calculation, and AST conversion."""

    def __init__(
        self,
        formula_repo: FormulaRepo,
        gemini_client: GeminiClient,
        patient_field_repo: PatientFieldRepo | None = None,
        ai_chat_session_repo: AiChatSessionRepo | None = None,
        ai_chat_message_repo: AiChatMessageRepo | None = None,
    ):
        self.formula_repo = formula_repo
        self.patient_field_repo = patient_field_repo
        self.ai_chat_session_repo = ai_chat_session_repo
        self.ai_chat_message_repo = ai_chat_message_repo
        self.formula_generator = FormulaGenerator(gemini_client)
        self.yaml_parser = YamlParser()
        self.score_calculator = ScoreCalculator()
        self.risk_assessor = RiskAssessor()

    def chat(
        self,
        message: str,
        patient_fields: list[dict] | None = None,
        attachments: list[dict] | None = None,
    ) -> ChatResponse:
        """V1 mixed-mode chat."""
        reply_text, formula_description, yaml_content = self.formula_generator.chat(
            message=message,
            patient_fields=patient_fields,
            attachments=attachments,
        )
        return ChatResponse(
            reply=reply_text,
            formula_description=formula_description,
            generated_yaml=yaml_content,
        )

    def chat_v2(
        self,
        *,
        user_id: int,
        message: str,
        session_id: int | None = None,
        patient_fields: list[dict] | None = None,
        attachments: list[dict] | None = None,
        yaml_content: str | None = None,
        memory_window: int = 10,
    ) -> ChatV2Response:
        """V2 mixed-mode chat with persisted memory and YAML revision support."""
        if self.ai_chat_session_repo is None or self.ai_chat_message_repo is None:
            raise ValidationException("AI chat v2 repositories are not configured")

        session = self._resolve_chat_session(
            user_id=user_id,
            session_id=session_id,
            title_seed=message,
        )
        history_messages = self.ai_chat_message_repo.list_recent_by_session(
            session.id,
            limit=memory_window,
        )

        current_yaml = None
        yaml_source = "none"
        if yaml_content:
            current_yaml = yaml_content
            yaml_source = "request"
        elif getattr(session, "current_yaml", None):
            current_yaml = session.current_yaml
            yaml_source = "memory"
        else:
            last_yaml_message = self.ai_chat_message_repo.get_last_generated_yaml(
                session.id
            )
            if last_yaml_message and last_yaml_message.generated_yaml:
                current_yaml = last_yaml_message.generated_yaml
                yaml_source = "memory"

        self.ai_chat_message_repo.create(
            session_id=session.id,
            role="user",
            content=message,
            attachments=attachments,
        )

        reply_text, formula_description, generated_yaml = self.formula_generator.chat(
            message=message,
            patient_fields=patient_fields,
            attachments=attachments,
            conversation_history=[
                self._serialize_chat_message(item) for item in history_messages
            ],
            current_yaml=current_yaml,
        )

        self.ai_chat_message_repo.create(
            session_id=session.id,
            role="assistant",
            content=reply_text,
            formula_description=formula_description,
            generated_yaml=generated_yaml,
        )
        if generated_yaml is not None:
            self.ai_chat_session_repo.set_current_yaml(session.id, generated_yaml)
        elif yaml_content is not None:
            self.ai_chat_session_repo.set_current_yaml(session.id, yaml_content)
        self.ai_chat_session_repo.touch(session.id)

        return ChatV2Response(
            session_id=session.id,
            reply=reply_text,
            formula_description=formula_description,
            generated_yaml=generated_yaml,
            yaml_source=yaml_source,
            memory_message_count=len(history_messages),
        )

    def calculate_score(self, request: CalculateScoreRequest) -> ScoreResponse:
        """Calculate score from YAML content or a stored formula id."""
        yaml_content = self._resolve_yaml_content(
            yaml_content=request.yaml_content,
            formula_id=request.formula_id,
        )
        schema = self.yaml_parser.parse_yaml(yaml_content)
        module_scores, global_score = self.score_calculator.calculate_all(
            schema, request.variables
        )
        risk_level = self.risk_assessor.assess_risk(global_score, schema.risk_levels)
        return ScoreResponse(
            score_name=schema.score_name,
            module_scores=module_scores,
            global_score=global_score,
            risk_level=risk_level,
        )

    def extract_variables(
        self, request: ExtractVariablesRequest
    ) -> ExtractVariablesResponse:
        """Extract variables from YAML content or a stored formula id."""
        yaml_content = self._resolve_yaml_content(
            yaml_content=request.yaml_content,
            formula_id=request.formula_id,
        )
        schema = self.yaml_parser.parse_yaml(yaml_content)

        patient_field_names: set[str] = set()
        if self.patient_field_repo:
            patient_field_names = {
                pf.field_name for pf in self.patient_field_repo.list_all()
            }

        seen = set()
        variables = []
        for module in schema.modules:
            for var_name, var_def in module.variables.items():
                if var_name in seen:
                    continue
                seen.add(var_name)
                variables.append(
                    VariableInfo(
                        name=var_name,
                        var_type=var_def.type,
                        description=var_def.description,
                        module=module.name,
                        is_patient_field=var_name in patient_field_names,
                    )
                )

        return ExtractVariablesResponse(
            score_name=schema.score_name,
            variables=variables,
            yaml_content=yaml_content,
        )

    def convert_to_ast(self, request: ExtractVariablesRequest) -> Dict[str, Any]:
        """Convert YAML content or stored formula to Blockly-friendly AST."""
        yaml_content = self._resolve_yaml_content(
            yaml_content=request.yaml_content,
            formula_id=request.formula_id,
        )
        schema = self.yaml_parser.parse_yaml(yaml_content)
        return AstConverter.yaml_schema_to_ast(schema)

    def _resolve_yaml_content(
        self,
        *,
        yaml_content: str | None,
        formula_id: int | None,
    ) -> str:
        if formula_id:
            stored = self.formula_repo.get_by_id(formula_id)
            if stored is None:
                raise NotFoundException(f"Formula {formula_id} not found")
            return stored.yaml_content
        if yaml_content:
            return yaml_content
        raise ValidationException("Must provide yaml_content or formula_id")

    def _resolve_chat_session(
        self,
        *,
        user_id: int,
        session_id: int | None,
        title_seed: str,
    ):
        if self.ai_chat_session_repo is None:
            raise ValidationException("AI chat v2 repositories are not configured")

        if session_id is None:
            title = " ".join(title_seed.strip().split())[:80] or None
            return self.ai_chat_session_repo.create(user_id=user_id, title=title)

        session = self.ai_chat_session_repo.get_by_id_for_user(session_id, user_id)
        if session is None:
            raise NotFoundException(f"AI chat session {session_id} not found")
        return session

    @staticmethod
    def _serialize_chat_message(message: Any) -> Dict[str, Any]:
        return {
            "role": getattr(message, "role", None),
            "content": getattr(message, "content", getattr(message, "message", None)),
            "formula_description": getattr(message, "formula_description", None),
            "generated_yaml": getattr(message, "generated_yaml", None),
        }
