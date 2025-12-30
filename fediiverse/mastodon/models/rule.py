from pydantic import BaseModel


class Rule(BaseModel):
	id: str
	text: str
