from uuid import uuid4

from src.llm_router.domain.dataclasses import AIModel, UserModelPreference
from src.llm_router.infra.repository import (
    AIModelMapper,
    AIModelOrm,
    UserModelPreferenceMapper,
    UserModelPreferenceOrm,
)


class TestAIModelMapper:
    """
    Тесты для маппинга доменной сущности User в ORM модель и обратно
    """

    def test_to_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_to_entity`, чтобы разделить доменную модель и модель хранения."""
        model = AIModelOrm(
            name="gpt_oss_120b",
            provider="YANDEX",
        )

        entity = AIModelMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.name == model.name
        assert entity.provider == model.provider
        assert entity.is_active == model.is_active

    def test_from_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_from_entity`, чтобы разделить доменную модель и модель хранения."""
        entity = AIModel(name="gpt_oss_120b", provider="YANDEX")

        model = AIModelMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.name == entity.name
        assert model.provider == entity.provider
        assert model.is_active == entity.is_active


class TestUserPreferenceMapper:
    """
    Тесты для маппинга доменной модели приглашения в ORM и обратно
    """

    def test_to_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_to_entity`, чтобы разделить доменную модель и модель хранения."""
        model = UserModelPreferenceOrm(user_id=uuid4(), model_id=uuid4())

        entity = UserModelPreferenceMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at
        assert entity.user_id == model.user_id
        assert entity.model_id == model.model_id

    def test_from_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_from_entity`, чтобы разделить доменную модель и модель хранения."""
        entity = UserModelPreference(user_id=uuid4(), model_id=uuid4())

        model = UserModelPreferenceMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.updated_at == entity.updated_at
        assert model.user_id == entity.user_id
        assert model.model_id == entity.model_id
