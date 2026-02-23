"""
TaskService Unit Test：使用 in-memory Fake Repo 與 Mock GeminiClient 進行隔離測試。
不依賴資料庫，不發出 HTTP 請求，完全可離線執行。
"""
import pytest
from unittest.mock import MagicMock

from app.repositories.task_repo import TaskRepo
from app.services.ai.task_service import TaskService


def _make_service(gemini_return: str = "摘要結果") -> tuple[TaskService, TaskRepo]:
    """建立 TaskService，注入 Fake Repos 與 Mock Gemini Client"""
    task_repo = TaskRepo()   # In-memory Repo，可直接當 Fake 使用

    fake_item_repo = MagicMock()
    fake_item_repo.list_all.return_value = []

    mock_gemini = MagicMock()
    mock_gemini.summarize_items.return_value = gemini_return

    svc = TaskService(task_repo, fake_item_repo, mock_gemini)
    return svc, task_repo


@pytest.mark.asyncio
async def test_create_task_returns_task_id():
    """建立任務後應立即回傳 task_id，狀態為 pending"""
    svc, _ = _make_service()
    task = svc.create_summarize_task()

    assert task.task_id is not None
    assert task.status == "pending"
    assert any(e.event_type == "created" for e in task.events)


@pytest.mark.asyncio
async def test_execute_task_completed_successfully():
    """背景執行完成後 status 應為 completed，result 為 Gemini 回傳值"""
    expected_result = "這是一份商品摘要"
    svc, task_repo = _make_service(gemini_return=expected_result)

    task = svc.create_summarize_task()
    await svc.execute_task_background(task.task_id)

    updated = task_repo.get_task(task.task_id)
    assert updated.status == "completed"
    assert updated.result == expected_result


@pytest.mark.asyncio
async def test_execute_task_events_order():
    """Events 應依序包含 created, llm_request, llm_response, completed"""
    svc, task_repo = _make_service()
    task = svc.create_summarize_task()
    await svc.execute_task_background(task.task_id)

    event_types = [e.event_type for e in task_repo.get_task(task.task_id).events]
    assert event_types == ["created", "llm_request", "llm_response", "completed"]


@pytest.mark.asyncio
async def test_execute_task_failed_on_gemini_error():
    """Gemini 拋出例外時，Task status 應轉為 failed"""
    task_repo = TaskRepo()
    fake_item_repo = MagicMock()
    fake_item_repo.list_all.return_value = []

    mock_gemini = MagicMock()
    mock_gemini.summarize_items.side_effect = RuntimeError("API 連線失敗")

    svc = TaskService(task_repo, fake_item_repo, mock_gemini)
    task = svc.create_summarize_task()
    await svc.execute_task_background(task.task_id)

    updated = task_repo.get_task(task.task_id)
    assert updated.status == "failed"
    assert "API 連線失敗" in (updated.result or "")
