import logging
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from multiprocessing.pool import ThreadPool
from typing import Generator, List, Literal, Optional, Union

from bottle import Bottle, HTTPError, request, response

from sbs2 import Blob, Entry, EntryId, EntryMetadata, Library, LibraryId, SBS2
from sbs2.download import download
from sbs2.webapps import AbortResponseStatus, _ResourcePaths, abort, get_library_or_abort
from sbs2.webapps.templates import NavBarLink, TemplateContext

_logger = logging.getLogger('sbs2.webapps.intake')


_DownloadState = Union[
    Literal['Success'],
    Literal['Failed'],
    Literal['Initialized'],
    Literal['Downloading'],
    Literal['Writing']
]


@dataclass
class _DownloadStatus:
    url: str
    content_length: int = field(default=0)
    downloaded_bytes: int = field(default=0)
    written_bytes: int = field(default=0)
    state: _DownloadState = field(default='Initialized')

    def increment_bytes_downloaded(self, byte_count: int) -> None:
        self.downloaded_bytes += byte_count

    def increment_bytes_written(self, byte_count: int) -> None:
        self.written_bytes += byte_count

    @property
    def percent_complete(self) -> int:
        if self.state == 'Downloading':
            numerator = self.downloaded_bytes
        elif self.state == 'Writing':
            numerator = self.written_bytes
        else:
            numerator = None

        if numerator is not None and self.content_length is not None:
            return round(numerator * 100 / self.content_length)
        else:
            return 100

    @property
    def summary(self) -> str:
        if self.state == 'Downloading' or self.state == 'Writing':
            return f'{self.state} {self.percent_complete}%'
        else:
            return self.state

    @property
    def progress_class(self) -> str:
        if self.state == 'Success':
            return 'bg-success'
        elif self.state == 'Failed':
            return 'bg-danger'
        elif self.state == 'Writing':
            return 'progress-bar-striped bg-info'
        else:
            return 'progress-bar-striped'


_EntryIngestionState = Union[Literal['Success'], Literal['Failed'], Literal['Working']]


@dataclass
class _EntryIngestion:
    library_id: LibraryId
    entry_id: EntryId
    state: _EntryIngestionState = field(default='Working')
    downloads: List[_DownloadStatus] = field(default_factory=list)


@dataclass
class _DownloadInput:
    url: str
    content_type: Optional[str] = field(default=None)


class ConflictResolution(Enum):
    Skip = auto()
    Replace = auto()
    ReplaceIfMore = auto()


class _Ingestor:
    def __init__(self, thread_pool: ThreadPool) -> None:
        self.thread_pool = thread_pool
        self.entry_ingestions: List[_EntryIngestion] = list()

    def put_entry_with_url_content(
        self,
        library: Library,
        entry_id: EntryId,
        entry_metadata: EntryMetadata,
        download_inputs: List[_DownloadInput],
        conflict_resolution: ConflictResolution
    ) -> Optional[Entry]:
        for i in self.entry_ingestions:
            if i.library_id == library.library_id and i.entry_id == entry_id and i.state == 'Working':
                _logger.info(f'Skipping ingestion for entry {entry_id} in library {library.library_id}: '
                             'another ingestion for that entry is currently working')
                return None

        if ConflictResolution.Skip == conflict_resolution and library.entry_exists(entry_id):
            _logger.info(f'Skipping ingestion for entry {entry_id} in library {library.library_id}: '
                         'entry already exists and conflict resolution is Skip')
            return None
        elif ConflictResolution.ReplaceIfMore == conflict_resolution:
            existing_entry = library.get_entry(entry_id)
            if existing_entry and len(existing_entry.blob_sequence) >= len(download_inputs):
                _logger.info(f'Skipping ingestion for entry {entry_id} in library {library.library_id}: '
                             'entry already exists with as many blobs and conflict resolution is ReplaceIfMore')
                return None

        _logger.info(f'Starting ingestion for entry {entry_id} in library {library.library_id}')

        ingestion = _EntryIngestion(library_id=library.library_id, entry_id=entry_id)
        self.entry_ingestions.append(ingestion)

        try:
            def download_and_create_blob(download_input: _DownloadInput) -> Optional[Blob]:
                url = download_input.url
                dl_status = _DownloadStatus(url)
                ingestion.downloads.append(dl_status)
                try:
                    dl = download(url)
                    dl_status.content_length = dl.headers.content_length
                    if download_input.content_type:
                        dl.headers.content_type = download_input.content_type
                    dl_status.state = 'Downloading'
                    content = dl.read_content(dl_status.increment_bytes_downloaded)
                    dl_status.state = 'Writing'
                    blob = library.create_blob(content, dl_status.increment_bytes_written)
                    dl_status.state = 'Success'
                    _logger.debug(f'Successfully downloaded content from "{url}" and put it in library '
                                  f'{library.library_id} as blob {blob.blob_id}')
                    return blob
                except BaseException as ex:
                    _logger.error(f'Download of "{url}" failed: {ex}', exc_info=ex)
                    dl_status.state = 'Failed'
                    ingestion.state = 'Failed'
                    return None

            blobs = self.thread_pool.map(download_and_create_blob, download_inputs)

            if ingestion.state != 'Working':
                _logger.error(f'Failed to put entry {entry_id} in library {library.library_id}')
                return None

            entry = Entry(entry_id=entry_id, metadata=entry_metadata, blob_sequence=list(filter(None, blobs)))
            library.put_entry(entry)
            _logger.info(f'Put entry {entry_id} in library {library.library_id} successfully')

            ingestion.state = 'Success'
            return entry

        except BaseException as ex:
            _logger.error(f'Failed to put  entry {entry_id} in library {library.library_id}: {ex}', exc_info=ex)
            ingestion.state = 'Failed'
            return None


class _IntakeResourcePaths(_ResourcePaths):
    def __init__(self, prefix: Optional[str]) -> None:
        super().__init__(prefix)
        self.intake = self._apply_prefix('/Intake')


@contextmanager
def intake_application(
    sbs2: SBS2,
    thread_pool_size: int = 100,
    resource_path_prefix: Optional[str] = None,
    shared_template_context: Optional[TemplateContext] = None
) -> Generator[Bottle, None, None]:
    api = Bottle()

    thread_pool = ThreadPool(processes=thread_pool_size)
    ingestor = _Ingestor(thread_pool)

    resource_paths = _IntakeResourcePaths(resource_path_prefix)
    template_context = shared_template_context or TemplateContext()
    template_context.add_to_nav_bar(NavBarLink(label='Intake Status', url=resource_paths.intake))

    @api.get(resource_paths.intake)
    def get_intake_status():
        filter_state = request.query.get('state')
        ingestions = ingestor.entry_ingestions
        if filter_state:
            ingestions = [ingestion for ingestion in ingestions if ingestion.state == filter_state]
        return template_context.render_template(
            template_name='intakestatus',
            title='Intake Status',
            count=len(ingestions),
            count_by_state=sorted(Counter(i.state for i in ingestions).items(), key=lambda e: e[0]),
            ingestions=ingestions
        )

    @api.post(resource_paths.intake)
    def intake_entry():
        try:
            entry_intake = request.json

            cr_val = entry_intake.get('conflict_resolution')
            conflict_resolution = ConflictResolution[str(cr_val)] if cr_val else ConflictResolution.Skip

            library_id = entry_intake['library_id']
            library = get_library_or_abort(sbs2, library_id, AbortResponseStatus.BadRequest)

            if 'urls' in entry_intake['content']:
                download_inputs = [_DownloadInput(url=url) for url in entry_intake['content']['urls']]
            else:
                download_inputs = [_DownloadInput(**di) for di in entry_intake['content']['downloads']]

            ingestor_args = dict(
                library=library,
                entry_id=EntryId(entry_intake['entry_id']),
                entry_metadata=EntryMetadata.from_dict(entry_intake['entry_metadata']),
                download_inputs=download_inputs,
                conflict_resolution=conflict_resolution
            )
        except HTTPError:
            raise
        except BaseException:
            abort(AbortResponseStatus.BadRequest)

        thread_pool.apply_async(ingestor.put_entry_with_url_content, kwds=ingestor_args)

        response.status = 201
        response.set_header('Content-Type', 'application/json')
        return

    yield api

    thread_pool.close()
    thread_pool.join()
