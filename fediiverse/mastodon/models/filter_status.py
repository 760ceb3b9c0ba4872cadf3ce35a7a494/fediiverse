from pydantic import BaseModel


class FilterStatus(BaseModel):
    id: str
    status_id: str
