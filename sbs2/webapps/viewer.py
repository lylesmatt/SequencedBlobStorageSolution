from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlencode

from bottle import Bottle, HTTPResponse, request

from sbs2 import Blob, BlobId, Entry, EntryId, LibraryId, SBS2
from sbs2.webapps import _ResourcePaths, get_blob_as_file_or_abort, get_entry_or_abort, get_library_or_abort
from sbs2.webapps.templates import NavBarDropDown, NavBarLink, TemplateContext


class _ViewerResourcePaths(_ResourcePaths):
    def __init__(self, prefix: Optional[str]) -> None:
        super().__init__(prefix)
        self.libraries = self._apply_prefix('/Libraries')

    def blob(self, library_id: str, blob_id: str) -> str:
        return self._apply_prefix(f'/Libraries/{library_id}/Blobs/{blob_id}')

    def entries_in_library(self, library_id: str) -> str:
        return self._apply_prefix(f'/Libraries/{library_id}/Entries')

    def entry(self, library_id: str, entry_id: str) -> str:
        return self._apply_prefix(f'/Libraries/{library_id}/Entries/{entry_id}')


@dataclass
class _LibraryModel:
    library_id: str
    url: str


@dataclass
class _BlobModel:
    blob_id: str
    url: str
    preview_url: Optional[str]


@dataclass
class _TagModel:
    value: str


@dataclass
class _AttributeModel:
    key: str
    value: str


@dataclass
class _EntryModel:
    entry_id: str
    attributes: List[_AttributeModel]
    tags: List[_TagModel]
    blob_sequence: List[_BlobModel]
    url: str
    preview_url: Optional[str]


class _ModelFactory:
    def __init__(self, resource_paths: _ViewerResourcePaths) -> None:
        self.resource_paths = resource_paths

    def create_library(self, library_id: LibraryId) -> _LibraryModel:
        return _LibraryModel(library_id=library_id, url=self.resource_paths.entries_in_library(library_id))

    def create_blob(self, library_id: LibraryId, blob: Blob) -> _BlobModel:
        ct = blob.content.get_type()
        url = self.resource_paths.blob(library_id, blob.blob_id)
        return _BlobModel(
            blob_id=blob.blob_id,
            url=url,
            preview_url=url if ct.startswith('image/') else None
        )

    def create_entry(self, library_id: LibraryId, entry: Entry) -> _EntryModel:
        blob_sequence: List[_BlobModel] = [self.create_blob(library_id, blob) for blob in entry.blob_sequence]
        blobs_with_preview = [m for m in blob_sequence if m.preview_url]
        return _EntryModel(
            entry_id=entry.entry_id,
            attributes=[_AttributeModel(key=k, value=v) for k, v in sorted(entry.metadata.attributes.items())],
            tags=[_TagModel(value=t) for t in sorted(entry.metadata.tags)],
            blob_sequence=blob_sequence,
            url=self.resource_paths.entry(library_id, entry.entry_id),
            preview_url=blobs_with_preview[0].preview_url if blobs_with_preview else None
        )


def viewer_application(
    sbs2: SBS2,
    resource_path_prefix: Optional[str] = None,
    shared_template_context: Optional[TemplateContext] = None
) -> Bottle:
    api = Bottle()

    resource_paths = _ViewerResourcePaths(resource_path_prefix)
    model_factory = _ModelFactory(resource_paths)
    template_context = shared_template_context or TemplateContext()

    libraries_drop_down = NavBarDropDown(label='Libraries', url=resource_paths.libraries)
    for lib in sbs2.get_libraries():
        lib_id = lib.library_id
        url = resource_paths.entries_in_library(lib_id)
        libraries_drop_down.sub_links.append(NavBarLink(label=lib_id, url=url))
    template_context.add_to_nav_bar(libraries_drop_down)

    @api.get(resource_paths.libraries)
    def get_libraries() -> str:
        libraries = sbs2.get_libraries()
        return template_context.render_template(
            template_name='libraries',
            title='Libraries',
            libraries=[model_factory.create_library(library.library_id) for library in libraries]
        )

    @api.get(resource_paths.blob('<library_id>', '<blob_id>'))
    def get_blob_content(library_id: LibraryId, blob_id: BlobId) -> HTTPResponse:
        return get_blob_as_file_or_abort(sbs2, library_id, blob_id)

    @api.get(resource_paths.entries_in_library('<library_id>'))
    def get_entries_in_library(library_id: LibraryId) -> str:
        library = get_library_or_abort(sbs2, library_id)
        limit = int(request.query.get('limit', 24))
        after_val = request.query.get('after')
        after = EntryId(after_val) if after_val else None
        sort = request.query.get('sort', 'asc')
        reverse = sort.lower() == 'desc'

        entries = library.get_entries(limit=limit, after=after, reverse=reverse)
        entry_models = [model_factory.create_entry(library_id, e) for e in entries]

        if entry_models and len(entry_models) == limit:
            params = dict(limit=limit, after=entry_models[-1].entry_id, sort=sort)
            next_page_url = f'{resource_paths.entries_in_library(library_id)}?{urlencode(params)}'
        else:
            next_page_url = None

        return template_context.render_template(
            template_name='entries',
            title=f'Entries in {library_id}',
            entries=entry_models,
            next_page_url=next_page_url
        )

    @api.get(resource_paths.entry('<library_id>', '<entry_id>'))
    def get_entry(library_id: LibraryId, entry_id: EntryId) -> str:
        entry = get_entry_or_abort(sbs2, library_id, entry_id)
        return template_context.render_template(
            template_name='entry',
            title=f'Entry {entry.entry_id} in {library_id}',
            entry=model_factory.create_entry(library_id, entry)
        )

    return api
