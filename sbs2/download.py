from contextlib import closing
from dataclasses import dataclass
from hashlib import sha1
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Optional, Union
from urllib.request import Request, urlopen

from sbs2 import (
    BytesWrittenCallback,
    ContentBody,
    ContentLength,
    ContentType,
    SBS2Exception,
    _PrehashedContent,
    _copy,
    _get_content_type
)


@dataclass
class DownloadResponseHeaders:
    content_type: ContentType
    content_length: ContentLength


class DownloadedContent(_PrehashedContent):
    def __init__(self, headers: DownloadResponseHeaders, body: SpooledTemporaryFile[bytes], sha1_hash: str) -> None:
        self.headers = headers
        self.body = body
        self.sha1_hash = sha1_hash

    def get_type(self) -> ContentType:
        return self.headers.content_type

    def get_body(self) -> ContentBody:
        self.body.seek(0)
        return ContentBody(self.body)  # type: ignore

    def get_length(self) -> ContentLength:
        return self.headers.content_length

    def get_sha1_hash(self) -> str:
        return self.sha1_hash

    def __repr__(self) -> str:
        return f'<DownloadedContent: {self.sha1_hash, self.headers.content_type}>'


@dataclass
class DownloadResponse:
    def __init__(self, url: str, headers: DownloadResponseHeaders, body: BinaryIO) -> None:
        self.url = url
        self.headers = headers
        self._body = body

    def read_content(
        self,
        downloaded_chunk_callback: Optional[BytesWrittenCallback] = None,
        buffer_size: int = 50 * 1024 ** 2
    ) -> DownloadedContent:
        try:
            body_buffer = SpooledTemporaryFile(buffering=buffer_size)
            hasher = sha1()

            def write(buf: bytes) -> None:
                body_buffer.write(buf)
                hasher.update(buf)

            with closing(self._body) as body:
                _copy(body.read, write, downloaded_chunk_callback)

            return DownloadedContent(
                headers=self.headers,
                body=body_buffer,
                sha1_hash=hasher.hexdigest()
            )
        except BaseException as ex:
            raise SBS2Exception(f'Failed to read content from "{self.url}"') from ex


def download(url_or_request: Union[str, Request]) -> DownloadResponse:
    url = url_or_request.full_url if isinstance(url_or_request, Request) else url_or_request
    try:
        response = urlopen(url_or_request)

        headers = DownloadResponseHeaders(
            content_type=_get_content_type(response.headers.get('content-type')),
            content_length=ContentLength(int(response.headers.get('content-length', 0)))
        )

        return DownloadResponse(url, headers, response)
    except BaseException as ex:
        raise SBS2Exception(f'Failed to create download from "{url}"') from ex
