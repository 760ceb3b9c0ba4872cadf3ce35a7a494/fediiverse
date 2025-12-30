from pydantic import BaseModel

from .status import Status


class Context(BaseModel):
	ancestors: list[Status]
	descendants: list[Status]
