from uuid import uuid4

from src.llm_router.domain.dataclasses import AIModel, UserModelPreference


def test_create_ai_model():
    """Выполняет действие `test_create_ai_model`, чтобы поддержать основной сценарий модуля."""
    model = AIModel(name="gpt_oss_120b", provider="YANDEX")

    assert model.name == "gpt_oss_120b"
    assert model.provider == "YANDEX"
    assert model.is_active is True
    assert model.description is None
    assert model.context_parametrs is None


def test_mark_active_ai_model():
    """Выполняет действие `test_mark_active_ai_model`, чтобы поддержать основной сценарий модуля."""
    model = AIModel(name="gpt_oss_120b", provider="YANDEX")

    model.mark_is_not_active()

    assert model.name == "gpt_oss_120b"
    assert model.provider == "YANDEX"
    assert model.is_active is False


def test_create_user_preference():
    """Выполняет действие `test_create_user_preference`, чтобы поддержать основной сценарий модуля."""
    user_id = uuid4()
    model_id = uuid4()
    model = UserModelPreference(user_id=user_id, model_id=model_id)

    assert model.user_id == user_id
    assert model.model_id == model_id


def test_change_user_preference():
    """Выполняет действие `test_change_user_preference`, чтобы поддержать основной сценарий модуля."""
    user_id = uuid4()
    model_id = uuid4()
    new_model_id = uuid4()
    model = UserModelPreference(user_id=user_id, model_id=model_id)

    model.change_model(new_model_id)

    assert model.model_id == new_model_id
