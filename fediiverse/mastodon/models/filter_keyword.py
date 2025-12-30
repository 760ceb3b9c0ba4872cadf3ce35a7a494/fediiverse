from pydantic import BaseModel


class FilterKeyword(BaseModel):
    id: str
    keyword: str
    whole_word: bool
