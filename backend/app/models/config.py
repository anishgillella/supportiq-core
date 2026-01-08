from pydantic import BaseModel
from typing import List


class PageConfig(BaseModel):
    page2: List[str]
    page3: List[str]


class ConfigResponse(BaseModel):
    page2: List[str]
    page3: List[str]
