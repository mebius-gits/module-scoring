"""
Scoring YAML Schema - Pydantic Models。
定義 YAML 公式模板的完整結構：score_name, modules (variables, formulas, rules), risk_levels。
同時包含 API 請求/回應 Schema。
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ── YAML Schema 定義 ─────────────────────────────────────────────


class ConditionBlock(BaseModel):
    """條件區塊：支援 if / else 與複合邏輯 (and/or)"""
    condition: Optional[str] = Field(None, alias="if", description="條件表達式，例如 'age > 80'")
    is_else: bool = Field(False, description="是否為 else 區塊")
    value: Union[str, int, float] = Field(..., description="條件成立時的值或公式表達式")

    model_config = {"populate_by_name": True}


class FormulaDefinition(BaseModel):
    """公式定義：支援條件公式表 (conditions) 或直接數學表達式 (formula)"""
    name: str = Field(..., description="公式名稱，可被其他公式引用")
    description: str = Field("", description="公式用途說明")
    conditions: Optional[List[ConditionBlock]] = Field(None, description="條件公式表")
    formula: Optional[str] = Field(None, description="數學表達式，例如 'age_factor * gender_factor'")


class RuleDefinition(BaseModel):
    """規則定義：對 module 或 formula 做累加/權重"""
    condition: str = Field(..., alias="if", description="觸發條件")
    add: Union[float, str] = Field(0, description="條件成立時累加的分數，可為數字或公式名引用")

    model_config = {"populate_by_name": True}


class ModuleDefinition(BaseModel):
    """模組定義：包含 variables, formulas, rules"""
    name: str = Field(..., description="模組名稱")
    variables: Dict[str, str] = Field(default_factory=dict, description="變數名與資料型態的映射")
    formulas: List[FormulaDefinition] = Field(default_factory=list, description="公式列表")
    rules: List[RuleDefinition] = Field(default_factory=list, description="評分規則列表")


class RiskLevelDefinition(BaseModel):
    """風險等級定義：根據全局 score 對應風險文字"""
    condition: Optional[str] = Field(None, alias="if", description="條件，例如 'score >= 12'")
    is_else: bool = Field(False, description="是否為 else 區塊")
    text: str = Field(..., description="風險等級文字")

    model_config = {"populate_by_name": True}


class ScoringYamlSchema(BaseModel):
    """頂層 YAML 結構：score_name + modules + risk_levels"""
    score_name: str = Field(..., description="全局 Score 名稱")
    modules: List[ModuleDefinition] = Field(default_factory=list, description="模組列表")
    risk_levels: List[RiskLevelDefinition] = Field(default_factory=list, description="風險等級列表")


# ── API Request / Response Schema ────────────────────────────────


class GenerateFormulaRequest(BaseModel):
    """AI 公式生成請求"""
    text: str = Field(
        ...,
        min_length=1,
        description="模組描述文字，AI 將根據此描述生成 YAML 公式",
    )


class CalculateScoreRequest(BaseModel):
    """分數計算請求"""
    yaml_content: Optional[str] = Field(None, description="YAML 公式字串（與 formula_id 二選一）")
    formula_id: Optional[str] = Field(None, description="已儲存的公式 ID（與 yaml_content 二選一）")
    variables: Dict[str, Any] = Field(
        ...,
        description="所有模組的輸入變數，格式: {'age': 75, 'is_female': true, ...}",
    )


class ModuleScoreResult(BaseModel):
    """單一模組的計算結果"""
    module_name: str
    formula_results: Dict[str, Any] = Field(default_factory=dict, description="各公式計算結果")
    rules_applied: List[str] = Field(default_factory=list, description="觸發的規則說明")
    module_score: float = Field(0, description="模組累加分數 (rules 結果)")


class ScoreResponse(BaseModel):
    """完整計算回應"""
    score_name: str
    module_scores: Dict[str, ModuleScoreResult] = Field(default_factory=dict)
    global_score: float = Field(0, description="全局總分")
    risk_level: str = Field("", description="風險等級文字")


class FormulaStorageItem(BaseModel):
    """已儲存的公式資訊"""
    formula_id: str
    score_name: str
    yaml_content: str
    ast_data: Optional[Dict[str, Any]] = None
    module_count: int = 0





class ChatRequest(BaseModel):
    """混合模式聊天請求：一般對話 + 公式生成"""
    message: str = Field(
        ...,
        min_length=1,
        description="使用者訊息，AI 自動判斷是一般對話或公式生成請求",
    )


class ChatResponse(BaseModel):
    """混合模式聊天回應：對話回覆 + 可選的 YAML 公式"""
    reply: str = Field(..., description="AI 對話回覆（繁體中文）")
    generated_yaml: Optional[str] = Field(
        None, description="若 AI 判斷為公式請求，回傳生成的 YAML 公式字串"
    )


class ExtractVariablesRequest(BaseModel):
    """變數萃取請求：從 YAML 或 formula_id 解析出所有變數"""
    yaml_content: Optional[str] = Field(None, description="YAML 公式字串")
    formula_id: Optional[str] = Field(None, description="已儲存的公式 ID")


class VariableInfo(BaseModel):
    """單一變數的資訊"""
    name: str = Field(..., description="變數名稱")
    var_type: str = Field(..., description="變數型態: int, float, boolean")
    module: str = Field(..., description="所屬模組名稱")


class ExtractVariablesResponse(BaseModel):
    """變數萃取回應"""
    score_name: str
    variables: List[VariableInfo] = Field(default_factory=list, description="所有變數列表")
    yaml_content: str = Field("", description="解析的 YAML 內容 (供後續計算)")


