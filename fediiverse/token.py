import datetime

from cryptography.fernet import Fernet
from pydantic import BaseModel

from .storage import get_config

config = get_config()
fernet: Fernet = Fernet(config.secrets.session_token_secret_key)


class FediiverseToken(BaseModel):
    user_id: str
    domain: str
    acct: str
    access_token: str
    timestamp: datetime.datetime

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("ascii")

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.model_validate_json(data.decode("ascii"))

    def to_encrypted(self) -> str:
        return fernet.encrypt(self.to_bytes()).decode("ascii")

    @classmethod
    def from_encrypted(cls, data: str):
        return cls.from_bytes(fernet.decrypt(data))
