from dataclasses import dataclass
from unittest.mock import MagicMock

from app.services.ai.scoring_service import ScoringService


@dataclass
class _FakeSession:
    id: int
    user_id: int
    title: str | None
    current_yaml: str | None = None
    updated_at: object | None = None


@dataclass
class _FakeMessage:
    id: int
    session_id: int
    role: str
    content: str
    formula_description: str | None = None
    generated_yaml: str | None = None


class _FakeSessionRepo:
    def __init__(self):
        self._sessions: dict[int, _FakeSession] = {}
        self._next_id = 1

    def create(self, user_id: int, title: str | None = None) -> _FakeSession:
        session = _FakeSession(id=self._next_id, user_id=user_id, title=title)
        self._sessions[session.id] = session
        self._next_id += 1
        return session

    def get_by_id_for_user(
        self, session_id: int, user_id: int
    ) -> _FakeSession | None:
        session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            return session
        return None

    def touch(self, session_id: int) -> _FakeSession | None:
        return self._sessions.get(session_id)

    def set_current_yaml(
        self, session_id: int, yaml_content: str | None
    ) -> _FakeSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.current_yaml = yaml_content
        return session


class _FakeMessageRepo:
    def __init__(self):
        self._messages: list[_FakeMessage] = []
        self._next_id = 1

    def create(
        self,
        session_id: int,
        role: str,
        content: str,
        attachments: list[dict] | None = None,
        formula_description: str | None = None,
        generated_yaml: str | None = None,
    ) -> _FakeMessage:
        message = _FakeMessage(
            id=self._next_id,
            session_id=session_id,
            role=role,
            content=content,
            formula_description=formula_description,
            generated_yaml=generated_yaml,
        )
        self._messages.append(message)
        self._next_id += 1
        return message

    def list_recent_by_session(
        self, session_id: int, limit: int = 10
    ) -> list[_FakeMessage]:
        items = [m for m in self._messages if m.session_id == session_id]
        if limit > 0:
            return items[-limit:]
        return items

    def get_last_generated_yaml(self, session_id: int) -> _FakeMessage | None:
        for message in reversed(self._messages):
            if message.session_id == session_id and message.generated_yaml:
                return message
        return None


def _make_service(*responses: str):
    mock_gemini = MagicMock()
    mock_gemini.generate_content.side_effect = list(responses)
    service = ScoringService(
        formula_repo=MagicMock(),
        gemini_client=mock_gemini,
        ai_chat_session_repo=_FakeSessionRepo(),
        ai_chat_message_repo=_FakeMessageRepo(),
    )
    return service, mock_gemini


def test_chat_v2_creates_session_and_persists_messages():
    service, _ = _make_service("一般回覆")

    response = service.chat_v2(
        user_id=7,
        message="先打個招呼",
    )

    assert response.session_id == 1
    assert response.reply == "一般回覆"
    assert response.yaml_source == "none"
    assert response.memory_message_count == 0

    stored_messages = service.ai_chat_message_repo.list_recent_by_session(1, limit=10)
    assert [m.role for m in stored_messages] == ["user", "assistant"]
    assert stored_messages[0].content == "先打個招呼"
    assert stored_messages[1].content == "一般回覆"


def test_chat_v2_uses_previous_yaml_and_history_as_memory():
    first_response = (
        "這是第一版\n\n"
        "DESCRIPTION_START\n公式說明\nDESCRIPTION_END\n\n"
        "FORMULA_START\nscore_name: original\nmodules: []\nrisk_levels: []\nFORMULA_END"
    )
    second_response = "已更新設定"
    service, mock_gemini = _make_service(first_response, second_response)

    first = service.chat_v2(user_id=9, message="幫我建立公式")
    second = service.chat_v2(
        user_id=9,
        session_id=first.session_id,
        message="幫我把 risk level 改得更細",
    )

    second_prompt = mock_gemini.generate_content.call_args_list[1].args[0]

    assert second.session_id == first.session_id
    assert second.yaml_source == "memory"
    assert second.memory_message_count == 2
    assert "CURRENT YAML TO MODIFY" in second_prompt
    assert "score_name: original" in second_prompt
    assert "USER: 幫我建立公式" in second_prompt
    assert "ASSISTANT GENERATED YAML" in second_prompt


def test_chat_v2_prefers_explicit_yaml_over_memory_yaml():
    first_response = (
        "先產生舊版\n\n"
        "DESCRIPTION_START\n舊版說明\nDESCRIPTION_END\n\n"
        "FORMULA_START\nscore_name: old_yaml\nmodules: []\nrisk_levels: []\nFORMULA_END"
    )
    second_response = "已改用新 YAML"
    service, mock_gemini = _make_service(first_response, second_response)

    first = service.chat_v2(user_id=11, message="先建立舊版")
    explicit_yaml = "score_name: explicit_yaml\nmodules: []\nrisk_levels: []"

    second = service.chat_v2(
        user_id=11,
        session_id=first.session_id,
        message="請依照這份 YAML 新增年齡參數",
        yaml_content=explicit_yaml,
    )

    second_prompt = mock_gemini.generate_content.call_args_list[1].args[0]

    assert second.yaml_source == "request"
    assert second.memory_message_count == 2
    assert "CURRENT YAML TO MODIFY" in second_prompt
    assert explicit_yaml in second_prompt
