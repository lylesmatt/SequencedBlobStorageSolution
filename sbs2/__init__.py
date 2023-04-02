import mimetypes
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from typing import (
    Annotated,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    List,
    NewType,
    Optional,
    Set
)

import dacite
from annotated_types import Gt

BlobId = NewType('BlobId', str)
ContentType = NewType('ContentType', str)
ContentBody = NewType('ContentBody', BinaryIO)
ContentLength = NewType('ContentLength', int)


class SBS2Exception(BaseException):
    ...


class Content(ABC):
    @abstractmethod
    def get_type(self) -> ContentType: ...

    @abstractmethod
    def get_body(self) -> ContentBody: ...

    def get_length(self) -> ContentLength:
        length = 0

        def inc_length(nbw):
            nonlocal length
            length += nbw

        with self.get_body() as f:
            _copy(f.read, lambda m: None, inc_length)

        return ContentLength(length)


class _PrehashedContent(Content, ABC):
    @abstractmethod
    def get_sha1_hash(self) -> str: ...


def _get_content_type(
    content_type_val: Optional[str],
    default_content_type_val: str = 'binary/octet-stream'
) -> ContentType:
    return ContentType(content_type_val or default_content_type_val)


@dataclass
class Blob:
    blob_id: BlobId
    content: Content


AttributeKey = NewType('AttributeKey', str)
AttributeValue = NewType('AttributeValue', str)
Attributes = Dict[AttributeKey, AttributeValue]
Tag = NewType('Tag', str)
Tags = Set[Tag]


@dataclass
class EntryMetadata:
    attributes: Attributes = field(default_factory=dict)
    tags: Tags = field(default_factory=set)

    def as_dict(self) -> Dict[str, Any]:
        emd = asdict(self)
        emd['tags'] = sorted(emd['tags'])
        return emd

    @staticmethod
    def from_dict(entry_metadata_dict: Dict[str, Any]) -> 'EntryMetadata':
        return dacite.from_dict(EntryMetadata, entry_metadata_dict, config=dacite.Config(type_hooks={Tags: set}))


EntryId = NewType('EntryId', str)
BlobSequence = List[Blob]


@dataclass
class Entry:
    entry_id: EntryId
    metadata: EntryMetadata
    blob_sequence: BlobSequence

    def as_dict(self) -> Dict[str, Any]:
        return dict(
            entry_id=self.entry_id,
            metadata=self.metadata.as_dict(),
            blob_sequence=[b.blob_id for b in self.blob_sequence]
        )


LibraryId = NewType('LibraryId', str)
PositiveInt = Annotated[int, Gt(0)]
BytesWrittenCallback = Callable[[int], None]


class Library(ABC):
    def __init__(self, library_id: LibraryId) -> None:
        self.library_id = library_id

    @abstractmethod
    def get_entry(self, entry_id: EntryId) -> Optional[Entry]: ...

    def entry_exists(self, entry_id: EntryId) -> bool:
        return self.get_entry(entry_id) is not None

    @abstractmethod
    def get_entries(
        self,
        limit: Optional[PositiveInt] = None,
        after: Optional[EntryId] = None,
        reverse: bool = False
    ) -> Iterable[Entry]: ...

    @abstractmethod
    def put_entry(self, entry: Entry) -> None: ...

    def create_entry(self, entry_id: EntryId, entry_metadata: EntryMetadata, content_sequence: List[Content]) -> Entry:
        blob_sequence = [self.create_blob(content) for content in content_sequence]
        entry = Entry(entry_id, entry_metadata, blob_sequence)
        self.put_entry(entry)
        return entry

    @abstractmethod
    def delete_entry(self, entry_id: EntryId) -> None: ...

    @abstractmethod
    def get_blob(self, blob_id: BlobId) -> Optional[Blob]: ...

    def blob_exists(self, blob_id: BlobId) -> bool:
        return self.get_blob(blob_id) is not None

    def create_blob(self, content: Content, write_callback: Optional[BytesWrittenCallback] = None) -> Blob:
        if isinstance(content, _PrehashedContent):
            sha1_hash = content.get_sha1_hash()
        else:
            hasher = sha1()
            with content.get_body() as f:
                _copy(f.read, hasher.update)
            sha1_hash = hasher.hexdigest()

        ext = mimetypes.guess_extension(content.get_type())
        if not ext:
            ext = ''
        elif ext == '.jpe':
            ext = '.jpg'

        blob_id = BlobId(sha1_hash + ext)

        existing_blob = self.get_blob(blob_id)
        if existing_blob:
            return existing_blob
        return self._write_blob_content(blob_id, content, write_callback)

    @abstractmethod
    def _write_blob_content(
        self,
        blob_id: BlobId,
        content: Content,
        write_callback: Optional[BytesWrittenCallback] = None
    ) -> Blob: ...

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.library_id}>'


class SBS2:
    def __init__(self, *libraries: Library) -> None:
        self._libraries_by_id = {library.library_id: library for library in libraries}

    def get_library(self, library_id: LibraryId) -> Optional[Library]:
        return self._libraries_by_id.get(library_id)

    def get_libraries(self) -> Iterable[Library]:
        return sorted(self._libraries_by_id.values(), key=lambda library: library.library_id)

    def __repr__(self) -> str:
        return f'<SBS2: {self.get_libraries()}>'


_default_chunk_size = 1024 * 1024


def _copy(
    reader: Callable[[int], Optional[bytes]],
    writer: Callable[[bytes], Any],
    callback: Optional[BytesWrittenCallback] = None,
    chunk_size: Optional[int] = None
) -> None:
    n = chunk_size or _default_chunk_size
    while True:
        buf = reader(n)
        if not buf:
            break
        writer(buf)
        if callback:
            callback(len(buf))


def _copy_fileobj(
    src: BinaryIO,
    dest: BinaryIO,
    callback: Optional[BytesWrittenCallback] = None,
    chunk_size: Optional[int] = None
) -> None:
    _copy(src.read, dest.write, callback, chunk_size)
