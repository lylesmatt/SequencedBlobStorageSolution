from pathlib import Path
from typing import Optional, Iterable, Dict, Tuple

from sqlitedict import SqliteDict

from sbs2 import EntryId, Entry, PositiveInt, BlobId, LibraryId, EntryMetadata
from sbs2.filesystem import AbstractFileContentLibrary, PathLike

class _SqliteDict(SqliteDict):
    def items_page(
        self,
        limit: Optional[PositiveInt] = None,
        after: Optional[str] = None,
        reverse: bool = False
    ) -> Iterable[Tuple[str, Dict]]:
        query = 'SELECT key, value FROM "%s"' % self.tablename
        if after:
            if reverse:
                query += ' WHERE key < "%s"' % after
            else:
                query += ' WHERE key > "%s"' % after
        query += ' ORDER BY key'
        if reverse:
            query += ' DESC'
        if limit:
            query += ' LIMIT %d' % limit

        for key, value in self.conn.select(query):
            yield self.decode_key(key), self.decode(value)


class SqliteLibrary(AbstractFileContentLibrary):
    def __init__(self, library_file_pathlike: PathLike) -> None:
        library_file_path = Path(library_file_pathlike)
        super().__init__(LibraryId(library_file_path.name))
        self._entry_db = _SqliteDict(library_file_path.joinpath('entries.db'), autocommit=True)
        self._blobs_path = library_file_path.joinpath('Blobs')
        self._blobs_path.mkdir(exist_ok=True)

    def _get_blob_file_path(self, blob_id: BlobId) -> Path:
        return self._blobs_path.joinpath(blob_id)

    def _entry_from_dict(self, entry_id: str, entry_data: Dict) -> Entry:
        return Entry(
            entry_id=EntryId(entry_id),
            metadata=EntryMetadata.from_dict(entry_data['metadata']),
            blob_sequence=self._get_blob_sequence(entry_data['blob_sequence']),
        )

    def get_entry(self, entry_id: EntryId) -> Optional[Entry]:
        entry_data = self._entry_db.get(entry_id)
        if not entry_data:
            return None
        return self._entry_from_dict(entry_id, entry_data)

    def get_entries(
        self,
        limit: Optional[PositiveInt] = None,
        after: Optional[EntryId] = None,
        reverse: bool = False
    ) -> Iterable[Entry]:
        return map(lambda t: self._entry_from_dict(*t), self._entry_db.items_page(limit, after, reverse))

    def put_entry(self, entry: Entry) -> None:
        entry_dict = entry.as_dict()
        del entry_dict['entry_id']
        self._entry_db[entry.entry_id] = entry_dict

    def delete_entry(self, entry_id: EntryId) -> None:
        del self._entry_db[entry_id]
