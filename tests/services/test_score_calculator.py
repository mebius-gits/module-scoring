"""
Score Calculator / YAML Parser / Risk Assessor 單元測試。
使用 Cockcroft-Gault 範例 YAML 進行端到端驗證。
含複雜數學公式、module_name 別名、Pipeline 整合測試。
不依賴資料庫，不發出 HTTP 請求，完全可離線執行。
"""
import pytest
from unittest.mock import MagicMock

from app.services.ai.yaml_parser import YamlParser
from app.services.ai.score_calculator import ScoreCalculator
from app.services.ai.risk_assessor import RiskAssessor
from app.services.ai.scoring_service import ScoringService
from app.models.scoring import (
    CalculateScoreRequest,
    ConditionBlock,
    FormulaDefinition,
    ModuleDefinition,
    RiskLevelDefinition,
    RuleDefinition,
    ScoringYamlSchema,
)


# ── 測試用 YAML 範例 ──────────────────────────────────────────────

EXAMPLE_YAML = """
score_name: Cockcroft_Gault_Creatinine_Clearance

modules:
  - name: Demographics
    variables:
      age: int
      is_female: boolean
    formulas:
      - name: age_factor
        description: "Weighting factor based on age"
        conditions:
          - if: age > 80
            value: 3
          - if: age > 60
            value: 2
          - else:
            value: 1
      - name: gender_factor
        description: "Adjustment factor for female"
        conditions:
          - if: is_female
            value: 0.85
          - else:
            value: 1
      - name: demo_score
        description: "Demographics module score = age_factor * gender_factor"
        formula: "age_factor * gender_factor"
    rules:
      - if: age_factor > 2
        add: 1
      - if: gender_factor < 1
        add: 0.5

  - name: CardiacMarkers
    variables:
      troponin_level: int
      ecg_score: int
    formulas:
      - name: cardiac_risk_factor
        description: "Cardiac risk contribution"
        conditions:
          - if: troponin_level >= 2 and ecg_score >= 2
            value: 3
          - if: troponin_level >= 1 or ecg_score >= 1
            value: 1.5
          - else:
            value: 0
    rules:
      - if: cardiac_risk_factor >= 2
        add: 1

  - name: HistoryRisk
    variables:
      history_score: int
      risk_factor_count: int
    formulas:
      - name: history_module_score
        description: "History-based risk score"
        conditions:
          - if: history_score >= 2 and risk_factor_count >= 3
            value: 3
          - if: history_score >= 1 and risk_factor_count >= 1
            value: 1
          - else:
            value: 0
    rules:
      - if: history_module_score >= 2
        add: 1

risk_levels:
  - if: score >= 12
    text: "High Risk - requires urgent intervention"
  - if: score >= 6
    text: "Medium Risk - consider observation"
  - else:
    text: "Low Risk - standard care"
"""

# 含複雜數學公式的 YAML (Cockcroft-Gault 真實計算)
COMPLEX_FORMULA_YAML = """
score_name: Cockcroft_Gault_Real

modules:
  - name: RenalFunction
    variables:
      age: int
      weight: int
      serum_creatinine: float
      is_female: boolean
    formulas:
      - name: male_base_clearance
        description: "CrCl for male = ((140 - age) * weight) / (72 * serum_creatinine)"
        formula: "((140 - age) * weight) / (72 * serum_creatinine)"
      - name: gender_adjustment
        description: "Gender adjustment factor"
        conditions:
          - if: is_female
            value: 0.85
          - else:
            value: 1
      - name: adjusted_clearance
        description: "Final adjusted clearance"
        formula: "male_base_clearance * gender_adjustment"
    rules:
      - if: adjusted_clearance < 30
        add: 3
      - if: adjusted_clearance < 60
        add: 1

risk_levels:
  - if: score >= 3
    text: "Severe Renal Impairment"
  - if: score >= 1
    text: "Moderate Renal Impairment"
  - else:
    text: "Normal Renal Function"
"""

# 使用 module_name (AI 可能輸出的格式)
MODULE_NAME_ALIAS_YAML = """
score_name: Test_Module_Name_Alias

modules:
  - module_name: DemoModule
    variables:
      x: int
    formulas:
      - name: test_val
        conditions:
          - if: x > 10
            value: 2
          - else:
            value: 0
    rules:
      - if: test_val >= 2
        add: 1

risk_levels:
  - if: score >= 1
    text: "High"
  - else:
    text: "Low"
"""


# ── 1. 條件評估測試 ──────────────────────────────────────────────


class TestEvaluateCondition:
    """測試條件表達式評估"""

    def test_simple_greater_than_true(self):
        assert ScoreCalculator.evaluate_condition("age > 80", {"age": 85}) is True

    def test_simple_greater_than_false(self):
        assert ScoreCalculator.evaluate_condition("age > 80", {"age": 70}) is False

    def test_greater_equal(self):
        assert ScoreCalculator.evaluate_condition("score >= 12", {"score": 12}) is True

    def test_less_than(self):
        assert ScoreCalculator.evaluate_condition("weight < 50", {"weight": 45}) is True

    def test_boolean_variable(self):
        assert ScoreCalculator.evaluate_condition("is_female", {"is_female": True}) is True
        assert ScoreCalculator.evaluate_condition("is_female", {"is_female": False}) is False

    def test_compound_and(self):
        ctx = {"serum_creatinine": 3, "weight": 45}
        assert ScoreCalculator.evaluate_condition(
            "serum_creatinine > 2 and weight < 50", ctx
        ) is True

    def test_compound_and_false(self):
        ctx = {"serum_creatinine": 3, "weight": 60}
        assert ScoreCalculator.evaluate_condition(
            "serum_creatinine > 2 and weight < 50", ctx
        ) is False

    def test_compound_or(self):
        ctx = {"troponin_level": 0, "ecg_score": 2}
        assert ScoreCalculator.evaluate_condition(
            "troponin_level >= 1 or ecg_score >= 1", ctx
        ) is True

    def test_not_condition(self):
        assert ScoreCalculator.evaluate_condition(
            "not is_female", {"is_female": False}
        ) is True


# ── 2. 公式計算測試 ──────────────────────────────────────────────


class TestEvaluateFormula:
    """測試公式評估"""

    def test_conditions_formula_match_first(self):
        """age_factor: age=85 -> value 3"""
        formula = FormulaDefinition(
            name="age_factor",
            description="test",
            conditions=[
                ConditionBlock(condition="age > 80", value=3),
                ConditionBlock(condition="age > 60", value=2),
                ConditionBlock(is_else=True, value=1),
            ],
        )
        result = ScoreCalculator.evaluate_formula(formula, {"age": 85})
        assert result == 3

    def test_conditions_formula_match_second(self):
        """age_factor: age=65 -> value 2"""
        formula = FormulaDefinition(
            name="age_factor",
            description="test",
            conditions=[
                ConditionBlock(condition="age > 80", value=3),
                ConditionBlock(condition="age > 60", value=2),
                ConditionBlock(is_else=True, value=1),
            ],
        )
        result = ScoreCalculator.evaluate_formula(formula, {"age": 65})
        assert result == 2

    def test_conditions_formula_else(self):
        """age_factor: age=30 -> value 1 (else)"""
        formula = FormulaDefinition(
            name="age_factor",
            description="test",
            conditions=[
                ConditionBlock(condition="age > 80", value=3),
                ConditionBlock(condition="age > 60", value=2),
                ConditionBlock(is_else=True, value=1),
            ],
        )
        result = ScoreCalculator.evaluate_formula(formula, {"age": 30})
        assert result == 1

    def test_expression_formula(self):
        """demo_score = age_factor * gender_factor"""
        formula = FormulaDefinition(
            name="demo_score",
            description="test",
            formula="age_factor * gender_factor",
        )
        ctx = {"age_factor": 3, "gender_factor": 0.85}
        result = ScoreCalculator.evaluate_formula(formula, ctx)
        assert abs(result - 2.55) < 0.001


# ── 3. 模組計算測試 ──────────────────────────────────────────────


class TestCalculateModule:
    """測試模組計算"""

    def test_demographics_module_old_female(self):
        """年長女性: age_factor=3, gender_factor=0.85, rules: +1 +0.5 = 1.5"""
        module = ModuleDefinition(
            name="Demographics",
            variables={"age": "int", "is_female": "boolean"},
            formulas=[
                FormulaDefinition(
                    name="age_factor",
                    conditions=[
                        ConditionBlock(condition="age > 80", value=3),
                        ConditionBlock(condition="age > 60", value=2),
                        ConditionBlock(is_else=True, value=1),
                    ],
                ),
                FormulaDefinition(
                    name="gender_factor",
                    conditions=[
                        ConditionBlock(condition="is_female", value=0.85),
                        ConditionBlock(is_else=True, value=1),
                    ],
                ),
                FormulaDefinition(
                    name="demo_score",
                    formula="age_factor * gender_factor",
                ),
            ],
            rules=[
                RuleDefinition(condition="age_factor > 2", add=1),
                RuleDefinition(condition="gender_factor < 1", add=0.5),
            ],
        )

        variables = {"age": 85, "is_female": True}
        shared_ctx = {}
        result = ScoreCalculator.calculate_module(module, variables, shared_ctx)

        assert result.module_name == "Demographics"
        assert result.formula_results["age_factor"] == 3
        assert result.formula_results["gender_factor"] == 0.85
        assert abs(result.formula_results["demo_score"] - 2.55) < 0.001
        assert result.module_score == 1.5
        assert len(result.rules_applied) == 2

    def test_demographics_module_young_male(self):
        """年輕男性: age_factor=1, gender_factor=1, rules: 無 = 0"""
        module = ModuleDefinition(
            name="Demographics",
            variables={"age": "int", "is_female": "boolean"},
            formulas=[
                FormulaDefinition(
                    name="age_factor",
                    conditions=[
                        ConditionBlock(condition="age > 80", value=3),
                        ConditionBlock(condition="age > 60", value=2),
                        ConditionBlock(is_else=True, value=1),
                    ],
                ),
                FormulaDefinition(
                    name="gender_factor",
                    conditions=[
                        ConditionBlock(condition="is_female", value=0.85),
                        ConditionBlock(is_else=True, value=1),
                    ],
                ),
                FormulaDefinition(
                    name="demo_score",
                    formula="age_factor * gender_factor",
                ),
            ],
            rules=[
                RuleDefinition(condition="age_factor > 2", add=1),
                RuleDefinition(condition="gender_factor < 1", add=0.5),
            ],
        )

        variables = {"age": 30, "is_female": False}
        shared_ctx = {}
        result = ScoreCalculator.calculate_module(module, variables, shared_ctx)

        assert result.formula_results["age_factor"] == 1
        assert result.formula_results["gender_factor"] == 1
        assert result.module_score == 0
        assert len(result.rules_applied) == 0


# ── 4. YAML 解析測試 ──────────────────────────────────────────────


class TestYamlParser:
    """測試 YAML 解析器"""

    def test_parse_example_yaml(self):
        schema = YamlParser.parse_yaml(EXAMPLE_YAML)
        assert schema.score_name == "Cockcroft_Gault_Creatinine_Clearance"
        assert len(schema.modules) == 3
        assert len(schema.risk_levels) == 3

    def test_parse_module_names(self):
        schema = YamlParser.parse_yaml(EXAMPLE_YAML)
        names = [m.name for m in schema.modules]
        assert names == ["Demographics", "CardiacMarkers", "HistoryRisk"]

    def test_parse_invalid_yaml(self):
        from app.common.exceptions import ValidationException
        with pytest.raises(ValidationException, match="YAML"):
            YamlParser.parse_yaml("{{invalid yaml")

    def test_parse_missing_score_name(self):
        from app.common.exceptions import ValidationException
        with pytest.raises(ValidationException, match="score_name"):
            YamlParser.parse_yaml("modules: []")

    def test_parse_module_name_alias(self):
        """支援 module_name 別名 (AI 可能輸出此格式)"""
        schema = YamlParser.parse_yaml(MODULE_NAME_ALIAS_YAML)
        assert schema.modules[0].name == "DemoModule"


# ── 5. Risk Assessor 測試 ────────────────────────────────────────


class TestRiskAssessor:
    """測試風險等級評估"""

    def _make_risk_levels(self):
        return [
            RiskLevelDefinition(condition="score >= 12", text="High Risk - requires urgent intervention"),
            RiskLevelDefinition(condition="score >= 6", text="Medium Risk - consider observation"),
            RiskLevelDefinition(is_else=True, text="Low Risk - standard care"),
        ]

    def test_high_risk(self):
        result = RiskAssessor.assess_risk(15, self._make_risk_levels())
        assert result == "High Risk - requires urgent intervention"

    def test_high_risk_boundary(self):
        result = RiskAssessor.assess_risk(12, self._make_risk_levels())
        assert result == "High Risk - requires urgent intervention"

    def test_medium_risk(self):
        result = RiskAssessor.assess_risk(8, self._make_risk_levels())
        assert result == "Medium Risk - consider observation"

    def test_medium_risk_boundary(self):
        result = RiskAssessor.assess_risk(6, self._make_risk_levels())
        assert result == "Medium Risk - consider observation"

    def test_low_risk(self):
        result = RiskAssessor.assess_risk(3, self._make_risk_levels())
        assert result == "Low Risk - standard care"

    def test_zero_score(self):
        result = RiskAssessor.assess_risk(0, self._make_risk_levels())
        assert result == "Low Risk - standard care"


# ── 6. 端到端整合測試 ────────────────────────────────────────────


class TestEndToEnd:
    """端到端: 解析 YAML -> 計算 -> 風險評估"""

    def test_full_pipeline_high_risk(self):
        schema = YamlParser.parse_yaml(EXAMPLE_YAML)
        variables = {
            "age": 85, "is_female": True,
            "troponin_level": 3, "ecg_score": 3,
            "history_score": 3, "risk_factor_count": 4,
        }
        module_scores, global_score = ScoreCalculator.calculate_all(schema, variables)
        assert module_scores["Demographics"].module_score == 1.5
        assert module_scores["CardiacMarkers"].module_score == 1.0
        assert module_scores["HistoryRisk"].module_score == 1.0
        assert global_score == 3.5
        risk = RiskAssessor.assess_risk(global_score, schema.risk_levels)
        assert risk == "Low Risk - standard care"

    def test_full_pipeline_low_risk(self):
        schema = YamlParser.parse_yaml(EXAMPLE_YAML)
        variables = {
            "age": 30, "is_female": False,
            "troponin_level": 0, "ecg_score": 0,
            "history_score": 0, "risk_factor_count": 0,
        }
        module_scores, global_score = ScoreCalculator.calculate_all(schema, variables)
        assert global_score == 0
        risk = RiskAssessor.assess_risk(global_score, schema.risk_levels)
        assert risk == "Low Risk - standard care"

    def test_scoring_service_calculate(self):
        mock_gemini = MagicMock()
        mock_formula_repo = MagicMock()
        svc = ScoringService(formula_repo=mock_formula_repo, gemini_client=mock_gemini)
        request = CalculateScoreRequest(
            yaml_content=EXAMPLE_YAML,
            variables={
                "age": 85, "is_female": True,
                "troponin_level": 3, "ecg_score": 3,
                "history_score": 3, "risk_factor_count": 4,
            },
        )
        response = svc.calculate_score(request)
        assert response.score_name == "Cockcroft_Gault_Creatinine_Clearance"
        assert response.global_score == 3.5
        assert "Low Risk" in response.risk_level


# ── 7. 複雜數學公式測試 ──────────────────────────────────────────


class TestComplexFormulas:
    """測試真實 Cockcroft-Gault 公式: ((140-age)*weight)/(72*creatinine)"""

    def test_cockcroft_gault_male(self):
        """男性: CrCl = ((140-75)*60)/(72*1.2) = 45.14"""
        schema = YamlParser.parse_yaml(COMPLEX_FORMULA_YAML)
        variables = {"age": 75, "weight": 60, "serum_creatinine": 1.2, "is_female": False}
        module_scores, global_score = ScoreCalculator.calculate_all(schema, variables)
        results = module_scores["RenalFunction"].formula_results

        expected = ((140 - 75) * 60) / (72 * 1.2)
        assert abs(results["male_base_clearance"] - expected) < 0.01
        assert results["gender_adjustment"] == 1
        assert abs(results["adjusted_clearance"] - expected) < 0.01
        assert global_score == 1.0  # 30 <= 45.14 < 60 -> +1

    def test_cockcroft_gault_female(self):
        """女性: CrCl * 0.85"""
        schema = YamlParser.parse_yaml(COMPLEX_FORMULA_YAML)
        variables = {"age": 75, "weight": 60, "serum_creatinine": 1.2, "is_female": True}
        module_scores, global_score = ScoreCalculator.calculate_all(schema, variables)
        results = module_scores["RenalFunction"].formula_results

        expected = ((140 - 75) * 60) / (72 * 1.2) * 0.85
        assert abs(results["adjusted_clearance"] - expected) < 0.01
        assert global_score == 1.0  # 30 <= 38.37 < 60 -> +1

    def test_cockcroft_gault_severe(self):
        """嚴重腎功能不全: 年長低體重高肌酐"""
        schema = YamlParser.parse_yaml(COMPLEX_FORMULA_YAML)
        variables = {"age": 90, "weight": 45, "serum_creatinine": 3.0, "is_female": True}
        module_scores, global_score = ScoreCalculator.calculate_all(schema, variables)
        results = module_scores["RenalFunction"].formula_results

        expected = ((140 - 90) * 45) / (72 * 3.0) * 0.85
        assert abs(results["adjusted_clearance"] - expected) < 0.01
        assert global_score == 4.0  # < 30 -> +3, also < 60 -> +1
        risk = RiskAssessor.assess_risk(global_score, schema.risk_levels)
        assert risk == "Severe Renal Impairment"

    def test_complex_parenthesized_expression(self):
        """直接測試含多層括號的表達式"""
        formula = FormulaDefinition(
            name="test",
            formula="((140 - age) * weight) / (72 * serum_creatinine)",
        )
        ctx = {"age": 75, "weight": 60, "serum_creatinine": 1.2}
        result = ScoreCalculator.evaluate_formula(formula, ctx)
        assert abs(result - ((140 - 75) * 60) / (72 * 1.2)) < 0.01

    def test_multi_term_arithmetic(self):
        """多項式運算"""
        formula = FormulaDefinition(name="test", formula="a + b * c - d / e")
        ctx = {"a": 10, "b": 3, "c": 4, "d": 6, "e": 2}
        result = ScoreCalculator.evaluate_formula(formula, ctx)
        assert result == 19.0  # 10 + 12 - 3


# ── 8. module_name 別名測試 ──────────────────────────────────────


class TestModuleNameAlias:
    """測試 YAML 中 module_name 作為 name 的別名"""

    def test_parse_module_name_alias(self):
        schema = YamlParser.parse_yaml(MODULE_NAME_ALIAS_YAML)
        assert schema.modules[0].name == "DemoModule"

    def test_calculate_with_module_name_alias(self):
        schema = YamlParser.parse_yaml(MODULE_NAME_ALIAS_YAML)
        module_scores, global_score = ScoreCalculator.calculate_all(schema, {"x": 15})
        assert module_scores["DemoModule"].formula_results["test_val"] == 2
        assert global_score == 1.0

    def test_calculate_module_name_alias_low(self):
        schema = YamlParser.parse_yaml(MODULE_NAME_ALIAS_YAML)
        module_scores, global_score = ScoreCalculator.calculate_all(schema, {"x": 5})
        assert module_scores["DemoModule"].formula_results["test_val"] == 0
        assert global_score == 0


# ── 9. Pipeline 整合測試 ─────────────────────────────────────────


class TestPipeline:
    """Pipeline 測試：確認 ScoringService 透過 formula_id 從 DB 讀取 YAML 並計算"""

    def test_calculate_with_formula_id_from_db(self):
        """透過 formula_id 從 mock FormulaRepo 取 YAML -> 計算 -> 回傳結果"""
        mock_gemini = MagicMock()

        # Mock FormulaRepo.get_by_id 回傳一個類 ORM 物件
        mock_formula_repo = MagicMock()
        mock_stored = MagicMock()
        mock_stored.yaml_content = COMPLEX_FORMULA_YAML
        mock_formula_repo.get_by_id.return_value = mock_stored

        svc = ScoringService(formula_repo=mock_formula_repo, gemini_client=mock_gemini)

        response = svc.calculate_score(CalculateScoreRequest(
            formula_id=1,
            variables={"age": 75, "weight": 60, "serum_creatinine": 1.2, "is_female": False},
        ))

        assert response.score_name == "Cockcroft_Gault_Real"
        assert "RenalFunction" in response.module_scores
        assert isinstance(response.global_score, float)
        assert response.risk_level != ""
        mock_formula_repo.get_by_id.assert_called_once_with(1)

    def test_calculate_formula_id_not_found(self):
        """當 formula_id 不存在時應拋出 NotFoundException"""
        from app.common.exceptions import NotFoundException
        mock_gemini = MagicMock()
        mock_formula_repo = MagicMock()
        mock_formula_repo.get_by_id.return_value = None

        svc = ScoringService(formula_repo=mock_formula_repo, gemini_client=mock_gemini)

        with pytest.raises(NotFoundException):
            svc.calculate_score(CalculateScoreRequest(
                formula_id=999,
                variables={"age": 75},
            ))

    def test_calculate_reuse_formula_with_different_variables(self):
        """Pipeline 生成的 formula_id 可用於後續 calculate"""
        mock_gemini = MagicMock()
        mock_formula_repo = MagicMock()
        mock_stored = MagicMock()
        mock_stored.yaml_content = COMPLEX_FORMULA_YAML
        mock_formula_repo.get_by_id.return_value = mock_stored

        svc = ScoringService(formula_repo=mock_formula_repo, gemini_client=mock_gemini)

        # 計算兩次，不同變數
        resp1 = svc.calculate_score(CalculateScoreRequest(
            formula_id=1,
            variables={"age": 75, "weight": 60, "serum_creatinine": 1.2, "is_female": False},
        ))
        resp2 = svc.calculate_score(CalculateScoreRequest(
            formula_id=1,
            variables={"age": 90, "weight": 45, "serum_creatinine": 3.0, "is_female": True},
        ))

        assert resp1.score_name == resp2.score_name
        assert resp1.global_score != resp2.global_score
