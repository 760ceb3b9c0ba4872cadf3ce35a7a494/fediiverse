from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, HttpUrl


class Rule(BaseModel):
	id: str
	text: str
