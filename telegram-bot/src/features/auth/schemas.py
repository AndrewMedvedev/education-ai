from pydantic import BaseModel, SecretStr


class Credentials(BaseModel):
    full_name: str
    login: str
    password: SecretStr
