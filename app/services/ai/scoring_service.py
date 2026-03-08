"""
Scoring Service：Orchestrator 服務層。
組合 FormulaGenerator、YamlParser、ScoreCalculator、RiskAssessor、FormulaRepo，
完成從生成到計算到風險評估的完整流程。
支援完整 Pipeline：病人資料 -> AI 分模組 -> 計算 -> 風險評估 -> JSON。
"""
from typing import Dict, Any, List

from app.infra.clients.gemini_client import GeminiClient
from app.models.scoring import (
    CalculateScoreRequest,
    ChatResponse,
    ExtractVariablesRequest,
    ExtractVariablesResponse,
    ScoreResponse,
    VariableInfo,
)
from app.repositories.formula_repo import FormulaRepo
from app.services.ai.formula_generator import FormulaGenerator
from app.services.ai.risk_assessor import RiskAssessor
from app.services.ai.score_calculator import ScoreCalculator
from app.services.ai.yaml_parser import YamlParser
from app.common.ast_converter import AstConverter


class ScoringService:
    """
    Scoring 商業邏輯層 - Orchestrator。
    遵循 Clean Architecture：不依賴 HTTP，只依賴 Repo 與 Infra Client。
    """

    def __init__(
        self,
        formula_repo: FormulaRepo,
        gemini_client: GeminiClient,
    ):
        self.formula_repo = formula_repo
        self.formula_generator = FormulaGenerator(gemini_client)
        self.yaml_parser = YamlParser()
        self.score_calculator = ScoreCalculator()
        self.risk_assessor = RiskAssessor()

    # ── 1. Mixed-mode Chat (聊天 + 公式生成) ──────────────────────

    def chat(
        self,
        message: str,
        patient_fields: list[dict] | None = None,
        attachments: list[dict] | None = None,
    ) -> ChatResponse:
        """
        混合模式聊天：AI 自動判斷一般對話或公式生成請求。
        當判斷為公式生成時，回傳生成的 YAML 字串（不自動儲存）。

        Args:
            message: 使用者自然語言訊息
            patient_fields: 從 DB 讀取的病人欄位列表（提供 AI 變數名稱提示）
            attachments: 使用者附加的檔案列表
        Returns:
            ChatResponse: 包含 reply + 可選 generated_yaml
        """
        reply_text, yaml_content = self.formula_generator.chat(
            message=message,
            patient_fields=patient_fields,
            attachments=attachments,
        )

        return ChatResponse(
            reply=reply_text,
            generated_yaml=yaml_content,
        )

    # ── 2. Score Calculator Skill ─────────────────────────────────

    def calculate_score(self, request: CalculateScoreRequest) -> ScoreResponse:
        """
        解析 YAML + 計算分數 + 評估風險。

        流程:
        1. 取得 YAML (直接提供或從 Repository 讀取)
        2. 解析為 ScoringYamlSchema
        3. 計算所有模組分數
        4. 累加全局分數
        5. 對應風險等級

        Args:
            request: 包含 yaml_content 或 formula_id，以及輸入變數
        Returns:
            ScoreResponse: 完整計算結果
        """
        # Step 1: 取得 YAML
        if request.formula_id:
            from app.common.exceptions import NotFoundException
            stored = self.formula_repo.get_by_id(request.formula_id)
            if stored is None:
                raise NotFoundException(f"Formula {request.formula_id} 不存在")
            yaml_content = stored.yaml_content
        elif request.yaml_content:
            yaml_content = request.yaml_content
        else:
            from app.common.exceptions import ValidationException
            raise ValidationException("必須提供 yaml_content 或 formula_id")

        # Step 2: 解析
        schema = self.yaml_parser.parse_yaml(yaml_content)

        # Step 3 & 4: 計算
        module_scores, global_score = self.score_calculator.calculate_all(
            schema, request.variables
        )

        # Step 5: 風險評估
        risk_level = self.risk_assessor.assess_risk(
            global_score, schema.risk_levels
        )

        return ScoreResponse(
            score_name=schema.score_name,
            module_scores=module_scores,
            global_score=global_score,
            risk_level=risk_level,
        )



    # ── 4. Extract Variables (變數萃取) ────────────────────────────

    def extract_variables(self, request: ExtractVariablesRequest) -> ExtractVariablesResponse:
        """
        從 YAML 或 formula_id 解析出所有變數定義。
        前端可用此資訊動態生成輸入表單。

        Args:
            request: 包含 yaml_content 或 formula_id
        Returns:
            ExtractVariablesResponse: score_name + 變數列表 + yaml_content
        """
        # 取得 YAML
        if request.formula_id:
            from app.common.exceptions import NotFoundException
            stored = self.formula_repo.get_by_id(request.formula_id)
            if stored is None:
                raise NotFoundException(f"Formula {request.formula_id} 不存在")
            yaml_content = stored.yaml_content
        elif request.yaml_content:
            yaml_content = request.yaml_content
        else:
            from app.common.exceptions import ValidationException
            raise ValidationException("必須提供 yaml_content 或 formula_id")

        # 解析
        schema = self.yaml_parser.parse_yaml(yaml_content)

        # 萃取變數 (跨模組去重)
        seen = set()
        variables = []
        for module in schema.modules:
            for var_name, var_def in module.variables.items():
                if var_name not in seen:
                    seen.add(var_name)
                    variables.append(VariableInfo(
                        name=var_name,
                        var_type=var_def.type,
                        description=var_def.description,
                        module=module.name,
                    ))

        return ExtractVariablesResponse(
            score_name=schema.score_name,
            variables=variables,
            yaml_content=yaml_content,
        )

    # ── 5. Convert to AST (與 Blockly 相容) ─────────────────────────

    def convert_to_ast(self, request: ExtractVariablesRequest) -> Dict[str, Any]:
        """
        將獨立的 YAML 或已儲存的公式，轉換為 Blockly 相容的 JSON AST 結構。
        """
        if request.formula_id:
            from app.common.exceptions import NotFoundException
            stored = self.formula_repo.get_by_id(request.formula_id)
            if stored is None:
                raise NotFoundException(f"Formula {request.formula_id} 不存在")
            yaml_content = stored.yaml_content
        elif request.yaml_content:
            yaml_content = request.yaml_content
        else:
            from app.common.exceptions import ValidationException
            raise ValidationException("必須提供 yaml_content 或 formula_id")

        schema = self.yaml_parser.parse_yaml(yaml_content)
        ast_data = AstConverter.yaml_schema_to_ast(schema)

        return ast_data
