import mimetypes
import re
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from typing import Any, Callable, Dict, IO, Iterable, List, Optional, Union

import yaml
from sortedcontainers import SortedKeyList

from sbs2 import (
    Blob,
    BlobId,
    BytesWrittenCallback,
    Content,
    ContentBody,
    ContentLength,
    ContentType,
    Entry,
    EntryId,
    EntryMetadata,
    Library,
    LibraryId,
    PositiveInt,
    SBS2Exception,
    _copy_fileobj,
    _get_content_type
)

PathLike = Union[Path, str]


def as_absolute_path(path_like: PathLike) -> Path:
    return (path_like if isinstance(path_like, Path) else Path(path_like)).absolute()


class FileContent(Content):
    def __init__(self, file_path: PathLike) -> None:
        self.file_path = as_absolute_path(file_path)

    def get_type(self) -> ContentType:
        return _get_content_type(mimetypes.guess_type(self.file_path)[0])

    def get_body(self) -> ContentBody:
        return ContentBody(self.file_path.open('rb'))

    def get_length(self) -> ContentLength:
        return ContentLength(self.file_path.stat().st_size)

    def __repr__(self) -> str:
        return f'<FileContent: {self.file_path}>'


@dataclass
class FileSystemEntryFileFormat:
    file_extension: str
    load: Callable[[IO], Dict]
    dump: Callable[[Dict, IO], Any]


yaml_entry_file_format = FileSystemEntryFileFormat(
    file_extension='.yaml',
    load=yaml.safe_load,
    dump=yaml.dump
)


def digit_value_aware_sort_key(value: str) -> List[Union[str, int]]:
    key_parts = re.split(r'(\d+)', value)
    sortable_key_parts = [int(p) if p.isdigit() else p for p in key_parts if p]
    return sortable_key_parts


@dataclass
class FileSystemLibraryConfig:
    entries_folder_relative_path: PathLike = field(default_factory=lambda: 'Entries')
    entry_file_format: FileSystemEntryFileFormat = field(default=yaml_entry_file_format)
    entry_id_sort_key: Callable[[EntryId], Any] = field(default=digit_value_aware_sort_key)
    blobs_folder_relative_path: PathLike = field(default_factory=lambda: 'Blobs')


class FileSystemLibrary(Library):
    def __init__(self, library_file_path: PathLike, config: Optional[FileSystemLibraryConfig] = None) -> None:
        self.library_file_path = as_absolute_path(library_file_path)
        super().__init__(LibraryId(self.library_file_path.name))
        self.library_file_path.mkdir(exist_ok=True)

        self.config = config or FileSystemLibraryConfig()

        self._entries_path = self.library_file_path.joinpath(self.config.entries_folder_relative_path)
        self._entries_path.mkdir(exist_ok=True)

        self._blobs_path = self.library_file_path.joinpath(self.config.blobs_folder_relative_path)
        self._blobs_path.mkdir(exist_ok=True)

    def _get_entry_file_path(self, entry_id: EntryId) -> Path:
        return self._entries_path.joinpath(entry_id).with_suffix(self.config.entry_file_format.file_extension)

    def _get_sorted_entry_file_paths(self) -> SortedKeyList[Path]:
        return SortedKeyList(
            iterable=self._entries_path.glob('*' + self.config.entry_file_format.file_extension),
            key=lambda efp: self.config.entry_id_sort_key(efp.stem)
        )

    def _load_entry(self, entry_file_path: Path) -> Entry:
        with entry_file_path.open('r') as f:
            try:
                entry_data = self.config.entry_file_format.load(f)
            except BaseException as ex:
                raise SBS2Exception(f'Unable to parse data for entry at "{entry_file_path}"') from ex

        def get_blob_unsafe(blob_id: BlobId) -> Blob:
            blob_file_path = self._get_blob_file_path(blob_id)
            return Blob(blob_id=blob_id, content=FileContent(blob_file_path))

        return Entry(
            entry_id=EntryId(entry_data['entry_id']),
            metadata=EntryMetadata.from_dict(entry_data['metadata']),
            blob_sequence=list(map(get_blob_unsafe, entry_data['blob_sequence']))
        )

    def _get_blob_file_path(self, blob_id: BlobId) -> Path:
        return self._blobs_path.joinpath(blob_id)

    def get_entry(self, entry_id: EntryId) -> Optional[Entry]:
        entry_file_path = self._get_entry_file_path(entry_id)
        if not entry_file_path.exists():
            return None
        return self._load_entry(entry_file_path)

    def entry_exists(self, entry_id: EntryId) -> bool:
        return self._get_entry_file_path(entry_id).exists()

    def get_entries(
        self,
        limit: Optional[PositiveInt] = None,
        after: Optional[EntryId] = None,
        reverse: bool = False
    ) -> Iterable[Entry]:
        all_entry_paths = self._get_sorted_entry_file_paths()

        after_key = self.config.entry_id_sort_key(after) if after else None
        if reverse:
            entry_file_paths = all_entry_paths.irange_key(max_key=after_key, inclusive=(False, False), reverse=True)
        else:
            entry_file_paths = all_entry_paths.irange_key(min_key=after_key, inclusive=(False, False))

        if limit:
            entry_file_paths = islice(entry_file_paths, limit)

        return map(self._load_entry, entry_file_paths)

    def put_entry(self, entry: Entry) -> None:
        entry_file_path = self._get_entry_file_path(entry.entry_id)
        entry_data = entry.as_dict()
        with entry_file_path.open('w') as f:
            self.config.entry_file_format.dump(entry_data, f)

    def delete_entry(self, entry_id: EntryId) -> None:
        self._get_entry_file_path(entry_id).unlink()

    def get_blob(self, blob_id: BlobId) -> Optional[Blob]:
        blob_file_path = self._get_blob_file_path(blob_id)
        if not blob_file_path.exists():
            return None
        return Blob(blob_id=blob_id, content=FileContent(blob_file_path))

    def blob_exists(self, blob_id: BlobId) -> bool:
        return self._get_blob_file_path(blob_id).exists()

    def _write_blob_content(
        self,
        blob_id: BlobId,
        content: Content,
        write_callback: Optional[BytesWrittenCallback] = None
    ) -> Blob:
        blob_file_path = self._get_blob_file_path(blob_id)
        with content.get_body() as src, blob_file_path.open('wb') as dst:
            _copy_fileobj(src, dst, write_callback)
        return Blob(blob_id=blob_id, content=FileContent(blob_file_path))
