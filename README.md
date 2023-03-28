# SequencedBlobStorageSolution

Sequenced Blob Storage Solution (SBS2) is a "buffet of utilities" to store and retrieve organized binary content using one or more backing storage technologies with a singular interface.

## Core Concepts

* `Blob` a normalized binary content, consisting of:
  * `Content` an abstract representation of binary data, with accessors to the body, MIME content type, and shortcut to the content length  
  * `BlobId` the SHA-1 hash + extension based on the content type 
* `Entry` a sequence of blobs with accompanying metadata. The `EntryId` is expected to be unique and sortable.
* `Library` a collection of entries and blobs.
* `SBS2` a collection of libraries.

## What's Included

Current types of libraries:
* `FileSystemLibrary`, where blobs and entries are represented on files on the designated file system.
* `AwsLibrary`, using S3 as blob storage and DynamoDB for entry storage.


Current web apps:
* `viewer` for listing libraries, paginating over entries, viewing entries, and getting blob contents via web browser.
* `intake` provides a resource to POST to add to a designated library by downloading remote content (represented as URLs) for the blobs and creating the accompanying entry, as well as a web browser page to see the current status.

## Getting Started

Here's a snippet of how everything can be configured to use together:

```python
from sbs2 import SBS2
from sbs2.aws import AwsLibrary, AwsResources
from sbs2.filesystem import FileSystemLibrary
from sbs2.webapps.viewer import viewer_application

if __name__ == '__main__':
    aws_resources = AwsResources(
        blob_s3_bucket_name='your.blob.bucket',
        entry_dynamo_table_name='your_entry_table'
    )
    
    sbs2 = SBS2(
        AwsLibrary('AwsLibrary', aws_resources),
        FileSystemLibrary('/path/to/library/FSLibrary')
    )
    
    viewer_app = viewer_application(sbs2)
    viewer_app.run()
```

## Testing and Validation

Included in the repo are integration tests and static analysis configuration for `mypy` and `flake8`.

The testing included is not intended to be complete, and only covers core functionality or to check against breaking errors. 

### AWS Tests

The AWS tests will create a new library for every test run. It's assumed the data will be removed by AWS, using lifecycles in S3 and TTL in DynamoDB. To facilitate the TTL in DynamoDB, a "ttl" attribute is included when putting the entry items.

You will need to configure which S3 bucket and DynamoDB library the tests use, via the `TEST_AWS_BLOB_S3_BUCKET` and `TEST_AWS_ENTRY_DYNAMODB_TABLE` environment variables respectively.

### Web App Tests

The web apps will start the web app on a background thread and make calls to it. The default port it runs on is `8081`. You can override this by setting the port value using the `TEST_VIEWER_WEBAPP_PORT` environment variable.