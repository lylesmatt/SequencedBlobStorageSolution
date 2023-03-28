import os
import types
import unittest
from datetime import datetime, timedelta
from time import mktime

import utils
from sbs2 import Entry, EntryMetadata
from sbs2.aws import AwsLibrary, AwsResources, S3ObjectContent

utils.patch_equals_key(S3ObjectContent, lambda c: c.s3_object.key)


now = datetime.now()


aws_resources = AwsResources(
    blob_s3_bucket_name=os.getenv('TEST_AWS_BLOB_S3_BUCKET'),
    entry_dynamo_table_name=os.getenv('TEST_AWS_ENTRY_DYNAMODB_TABLE')
)

entry_table = aws_resources.entry_dynamo_table
old_put_item = entry_table.put_item
ttl = int(mktime((now + timedelta(days=1)).timetuple()))


def put_item_with_ttl(self, Item):
    Item['ttl'] = ttl
    old_put_item(Item=Item)


entry_table.put_item = types.MethodType(put_item_with_ttl, entry_table)


library_id = now.strftime("TestRun-%Y%m%d-%H%M%S")
library = AwsLibrary(library_id, aws_resources)
print('Created library with ID ' + library_id)


class AwsLibraryTestCase(unittest.TestCase):
    def test_blob_create_get(self):
        write_counter = utils.WriteCounter()

        self.assertFalse(library.blob_exists(utils.red_png_blob_id), 'blob does not exist before put')

        blob = library.create_blob(utils.red_png_content, write_counter)
        self.assertEqual(blob.blob_id, utils.red_png_blob_id, 'created blob has same blob ID')
        self.assertEqual(
            blob.content.get_length(),
            utils.red_png_content.get_length(),
            'created blob has same content length'
        )
        self.assertEqual(
            blob.content.get_type(),
            utils.red_png_content.get_type(),
            'created blob has same content type'
        )
        with blob.content.get_body() as actual_body, utils.red_png_content.get_body() as expected_body:
            self.assertEqual(actual_body.read(), expected_body.read(), 'created blob has same body')
        self.assertEqual(1, write_counter.writes, 'write count after first create')

        self.assertTrue(library.blob_exists(utils.red_png_blob_id), 'blob exists after create')

        self.assertEqual(library.get_blob(utils.red_png_blob_id), blob, 'blob get is same as blob create')

        self.assertEqual(
            library.create_blob(utils.red_png_content, write_counter),
            blob,
            'blob from second create is same as blob from first create'
        )
        self.assertEqual(1, write_counter.writes, 'write count after second create')

    def test_entry_put_get_delete(self):
        blob_seq = [library.create_blob(c) for c in (utils.red_png_content, utils.blue_png_content)]

        entry_id = 'test'
        self.assertFalse(library.entry_exists(entry_id), 'entry does not exist before put')

        entry = Entry(
            entry_id=entry_id,
            metadata=EntryMetadata(
                attributes={'color': 'rb'},
                tags={'red', 'blue'}
            ),
            blob_sequence=blob_seq
        )
        library.put_entry(entry)

        self.assertTrue(library.entry_exists(entry_id), 'entry exists after put')

        self.assertEqual(library.get_entry(entry_id), entry, 'entry is same after put')

        library.delete_entry(entry_id)

        self.assertFalse(library.entry_exists(entry_id), 'entry does not exist after delete')

        self.assertIsNone(library.get_entry(entry_id), 'entry get returns None after delete')

    def test_entries_create_get(self):
        e1 = library.create_entry('e1', EntryMetadata(tags={'rgb'}), [utils.red_png_content])
        e10 = library.create_entry('e10', EntryMetadata(tags={'rgb'}), [utils.green_png_content])
        e2 = library.create_entry('e2', EntryMetadata(tags={'rgb'}), [utils.blue_png_content])
        e3 = library.create_entry('e3', EntryMetadata(tags={'bw'}), [utils.black_png_content])
        e100 = library.create_entry('e100', EntryMetadata(tags={'bw'}), [utils.white_png_content])

        self.assertEqual(list(library.get_entries()), [e1, e10, e100, e2, e3], 'get')
        self.assertEqual(list(library.get_entries(reverse=True)), [e3, e2, e100, e10, e1], 'get reversed')

        self.assertEqual(list(library.get_entries(limit=2)), [e1, e10], 'get limit')
        self.assertEqual(list(library.get_entries(limit=2, reverse=True)), [e3, e2], 'get limit reversed')

        self.assertEqual(list(library.get_entries(after='e10')), [e100, e2, e3], 'get after')
        self.assertEqual(list(library.get_entries(after='e2', reverse=True)), [e100, e10, e1], 'get after reversed')

        self.assertEqual(list(library.get_entries(limit=2, after='e1')), [e10, e100], 'get limit after')
        self.assertEqual(list(library.get_entries(limit=2, after='e3', reverse=True)), [e2, e100],
                         'get limit after reversed')


if __name__ == '__main__':
    unittest.main()
