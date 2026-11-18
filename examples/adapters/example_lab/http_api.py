"""Direct JSON requests to a configured instrument service."""

import json
from http.client import HTTPConnection, HTTPSConnection

from pydantic import AnyHttpUrl, field_validator

from scp_lab.execution_models import Contract


class ServiceConnection(Contract):
    base_url: AnyHttpUrl

    @field_validator("base_url")
    @classmethod
    def origin_only(cls, url):
        if (
            url.username is not None
            or url.password is not None
            or url.path not in (None, "/")
            or url.query is not None
            or url.fragment is not None
        ):
            raise ValueError("Use the service origin, including the port if required")
        return url

    def request(self, method, path, *, payload=None, headers=None):
        url = self.base_url
        connection = HTTPSConnection if url.scheme == "https" else HTTPConnection
        client = connection(url.host.strip("[]"), url.port, timeout=5)
        request_headers = {"Accept": "application/json", **(headers or {})}
        body = None
        if payload is not None:
            body = json.dumps(payload)
            request_headers["Content-Type"] = "application/json"
        try:
            client.request(method, path, body=body, headers=request_headers)
            response = client.getresponse()
            if response.status != 200:
                raise ValueError(f"{method} {path} returned HTTP {response.status}")
            content = response.read(65537)
            if len(content) > 65536:
                raise ValueError(f"{method} {path} returned an oversized response")
            return json.loads(content)
        finally:
            client.close()
