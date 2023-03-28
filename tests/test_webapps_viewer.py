import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import utils
from sbs2 import EntryMetadata, SBS2
from sbs2.filesystem import FileSystemLibrary
from sbs2.webapps.viewer import viewer_application

port = int(os.getenv('TEST_VIEWER_WEBAPP_PORT', 8081))


class ViewerWebAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.tmp_dir = TemporaryDirectory()
        library_path = Path(cls.tmp_dir.name).joinpath('Colors')
        library = FileSystemLibrary(library_path)

        library.create_entry(
            entry_id='rgb',
            entry_metadata=EntryMetadata(
                tags={'red', 'green', 'blue'}
            ),
            content_sequence=[
                utils.red_png_content,
                utils.green_png_content,
                utils.blue_png_content
            ]
        )

        library.create_entry(
            entry_id='bw',
            entry_metadata=EntryMetadata(
                tags={'black', 'white'}
            ),
            content_sequence=[
                utils.black_png_content,
                utils.white_png_content
            ]
        )

        viewer_app = viewer_application(SBS2(library))
        bg_thread = Thread(target=viewer_app.run, daemon=True, kwargs=dict(port=port))
        bg_thread.start()

    def assertResponseWithOkStatus(self, resource_path: str):
        resp = urlopen(f'http://localhost:{port}/{resource_path}')
        self.assertEqual(200, resp.status)

    def assertResponseWithNotFoundStatus(self, resource_path: str):
        try:
            urlopen(f'http://localhost:{port}/{resource_path}')
            self.fail()
        except HTTPError as ex:
            self.assertEqual(404, ex.status)

    def test_libraries(self):
        self.assertResponseWithOkStatus('Libraries')

    def test_blob(self):
        self.assertResponseWithOkStatus('Libraries/Colors/Blobs/' + utils.red_png_blob_id)

    def test_entries(self):
        self.assertResponseWithOkStatus('Libraries/Colors/Entries')

    def test_entry_found(self):
        self.assertResponseWithOkStatus('Libraries/Colors/Entries/rgb')

    def test_entry_not_found(self):
        self.assertResponseWithNotFoundStatus('Libraries/Colors/Entries/cmy')


if __name__ == '__main__':
    unittest.main()
