"""Defines the interface we use for requesting HTTP CRUD operations.
Note that every method should be asynchronous."""
from __future__ import annotations
from requests import Response
from typing import *

class Requester:
  async def get(self, url: str, *args, params: Dict[str, Any], **kwargs) -> Response:
    """Perform a `GET` request to the given `url`. Underlying API should support `params`."""
    raise NotImplementedError()
  
  async def post(self, url: str, *args, params: Dict[str, Any], **kwargs) -> Response:
    """Perform a `POST` request to the given `url`. Underlying API should support `params`."""
    raise NotImplementedError()
  
  async def put(self, url: str, *args, params: Dict[str, Any], **kwargs) -> Response:
    """Perform a `PUT` request to the given `url`. Underlying API should support `params`."""
    raise NotImplementedError()
  
  async def update(self, url: str, *args, params: Dict[str, Any], **kwargs) -> Response:
    """Synonymous for `Requester.put`."""
    raise NotImplementedError()
  
  async def delete(self, url: str, *args, params: Dict[str, Any], **kwargs) -> Response:
    """Perform a `DELETE` request to the given `url`. Underlying API should support `params`."""
    raise NotImplementedError()
