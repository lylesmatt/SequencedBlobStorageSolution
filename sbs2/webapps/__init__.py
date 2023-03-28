from abc import ABC
from enum import Enum
from typing import NoReturn, Optional

from bottle import HTTPError, HTTPResponse
from fdsend import send_file

from sbs2 import BlobId, Entry, EntryId, Library, LibraryId, SBS2


class AbortResponseStatus(Enum):
    BadRequest = 400
    NotFound = 404


def get_library_or_abort(
    sbs2: SBS2,
    library_id: LibraryId,
    abort_response_status: AbortResponseStatus = AbortResponseStatus.NotFound
) -> Library:
    library = sbs2.get_library(library_id)
    if not library:
        abort(abort_response_status, f'Library with ID = {library_id} not found')
    return library


def get_entry_or_abort(
    sbs2: SBS2,
    library_id: LibraryId,
    entry_id: EntryId,
    abort_response_status: AbortResponseStatus = AbortResponseStatus.NotFound
) -> Entry:
    library = get_library_or_abort(sbs2, library_id, abort_response_status)
    entry = library.get_entry(entry_id)
    if not entry:
        abort(abort_response_status, f'Entry with ID = {entry_id} not found in library {library_id}')
    return entry


def get_blob_as_file_or_abort(
    sbs2: SBS2,
    library_id: LibraryId,
    blob_id: BlobId,
    abort_response_status: AbortResponseStatus = AbortResponseStatus.NotFound
) -> HTTPResponse:
    library = get_library_or_abort(sbs2, library_id, abort_response_status)
    blob = library.get_blob(blob_id)
    if not blob:
        abort(abort_response_status, f'Blob with ID = {blob_id} not found in library {library_id}')
    return send_file(
        fd=blob.content.get_body(),
        ctype=blob.content.get_type(),
        size=blob.content.get_length(),
        filename=blob.blob_id
    )


def abort(abort_response_status: AbortResponseStatus, message: str) -> NoReturn:
    raise HTTPError(abort_response_status.value, message)


class _ResourcePaths(ABC):
    def __init__(self, prefix: Optional[str]) -> None:
        if prefix:
            prefix = prefix.removesuffix('/')
            if not prefix.startswith('/'):
                prefix = '/' + prefix
        self.prefix = prefix
        self.libraries = self._apply_prefix('/Libraries')

    def _apply_prefix(self, path: str) -> str:
        if self.prefix:
            return self.prefix + path
        return path
