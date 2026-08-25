from datetime import datetime, timezone

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def invalidate_active_for_user(self, user_id: int, used_at: datetime) -> None:
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: used_at}, synchronize_session=False)

    def create(self, token: PasswordResetToken) -> PasswordResetToken:
        return self.add(token)

    def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        return self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        ).first()

    def mark_used(self, token: PasswordResetToken, used_at: datetime) -> None:
        token.used_at = used_at
        self.db.commit()
