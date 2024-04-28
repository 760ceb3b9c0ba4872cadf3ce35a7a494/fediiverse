from __future__ import annotations
from typing import Union, Type, TypeVar, Any
from xml.etree import ElementTree

from fastapi import Response
from pydantic_xml import BaseXmlModel, BaseGenericXmlModel, element, XmlEncoder


class MiiverseXmlEncoder(XmlEncoder):
    def encode(self, obj: Any) -> str:
        if isinstance(obj, bool):
            return str(int(obj))
        return super().encode(obj)

#
# Result models
#


class BaseResultModel(BaseXmlModel, tag="result"):
    class Config:
        xml_encoders = {
            bool: lambda value: str(int(value))
        }

    has_error: bool = element()
    version: int = element()


class DiscoveryResultModelEndpoint(BaseXmlModel):
    host: str = element()
    api_host: str = element()
    portal_host: str = element()
    n3ds_host: str = element()


class DiscoveryResultModel(BaseResultModel):
    endpoint: DiscoveryResultModelEndpoint = element(tag="endpoint")


class DiscoveryResultErrorModel(BaseResultModel):
    code: int = element()
    error_code: int = element()
    message: str = element()


#
# response for result model
#
R = TypeVar("R", bound=BaseResultModel)


class MiiverseResultResponse(Response):
    media_type = "application/xml"

    def __init__(self, content: R, status_code: int = 200):
        super().__init__(content=content, status_code=status_code)

    def render(self, content: R) -> bytes:
        element = content.to_xml_tree(encoder=MiiverseXmlEncoder())
        ElementTree.indent(element, space="  ", level=0)
        return b'<?xml version="1.0" encoding="UTF-8" ?>\n' + ElementTree.tostring(element, encoding="utf-8") + b"\n"
