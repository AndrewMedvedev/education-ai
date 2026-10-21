
from src.shared.application.repos import Repository

from ..domain.entities import Feedback


class FeedbackRepository(Repository[Feedback]):
    """Операции хранения, необходимые для отзывов о платформе."""
