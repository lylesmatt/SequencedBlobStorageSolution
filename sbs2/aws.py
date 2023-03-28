from dataclasses import InitVar, dataclass, field
from typing import Dict, Iterable, Optional

import boto3
import boto3.dynamodb.conditions as dynamo_conditions
import botocore
from boto3_type_annotations.dynamodb.service_resource import Table
from boto3_type_annotations.s3.service_resource import Bucket, Object as S3Object

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
    Library,
    LibraryId,
    PositiveInt,
    SBS2Exception,
    _get_content_type
)


class S3ObjectContent(Content):
    def __init__(self, s3_object: S3Object) -> None:
        self.s3_object = s3_object

    def get_type(self) -> ContentType:
        return _get_content_type(self.s3_object.content_type)

    def get_body(self) -> ContentBody:
        return ContentBody(self.s3_object.get()['Body'])

    def get_length(self) -> ContentLength:
        return ContentLength(self.s3_object.content_length)

    def __repr__(self) -> str:
        return f'<S3ObjectContent: {self.s3_object.key}>'


@dataclass
class AwsResources:
    blob_s3_bucket_name: InitVar[str]
    entry_dynamo_table_name: InitVar[str]
    blob_s3_bucket: Bucket = field(init=False)
    entry_dynamo_table: Table = field(init=False)

    def __post_init__(self, blob_s3_bucket_name, entry_dynamo_table_name) -> None:
        self.blob_s3_bucket = boto3.resource('s3').Bucket(blob_s3_bucket_name)
        self.entry_dynamo_table = boto3.resource('dynamodb').Table(entry_dynamo_table_name)


class AwsLibrary(Library):
    def __init__(self, library_id: LibraryId, aws_resources: AwsResources) -> None:
        super().__init__(library_id)
        self.aws_resources = aws_resources

    def _to_entry_dynamo_key(self, entry_id: EntryId) -> Dict[str, str]:
        return {'library_id': self.library_id, 'entry_id': entry_id}

    def _to_blob_s3_key(self, blob_id: BlobId) -> str:
        return f'Libraries/{self.library_id}/Blobs/{blob_id}'

    def get_entry(self, entry_id: EntryId) -> Optional[Entry]:
        key = self._to_entry_dynamo_key(entry_id)
        item = self.aws_resources.entry_dynamo_table.get_item(Key=key).get('Item')
        if not item:
            return None
        return self._entry_from_dict(item)

    def get_entries(
        self,
        limit: Optional[PositiveInt] = None,
        after: Optional[EntryId] = None,
        reverse: bool = False
    ) -> Iterable[Entry]:
        query_params = dict(
            KeyConditionExpression=dynamo_conditions.Key('library_id').eq(self.library_id),
            ScanIndexForward=not reverse
        )
        if limit:
            query_params['Limit'] = limit
        if after:
            query_params['ExclusiveStartKey'] = self._to_entry_dynamo_key(after)

        while True:
            results = self.aws_resources.entry_dynamo_table.query(**query_params)
            items = results.get('Items')
            if not items:
                break
            yield from map(self._entry_from_dict, items)
            if limit:
                break
            last_evaluated_key = results.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
            query_params['ExclusiveStartKey'] = last_evaluated_key

    def put_entry(self, entry: Entry) -> None:
        item = entry.as_dict()
        item['library_id'] = self.library_id
        self.aws_resources.entry_dynamo_table.put_item(Item=item)

    def delete_entry(self, entry_id: EntryId) -> None:
        key = self._to_entry_dynamo_key(entry_id)
        self.aws_resources.entry_dynamo_table.delete_item(Key=key)

    def get_blob(self, blob_id: BlobId) -> Optional[Blob]:
        s3_key = self._to_blob_s3_key(blob_id)
        s3_object = self.aws_resources.blob_s3_bucket.Object(s3_key)
        try:
            # get an attribute of the object, which will result in a head request, and catch the 404 if no object
            s3_object.e_tag
            return Blob(
                blob_id=blob_id,
                content=S3ObjectContent(s3_object)
            )
        except botocore.exceptions.ClientError as ex:
            error_code = ex.response['Error']['Code']
            if error_code == '404':
                return None
            else:
                raise SBS2Exception(f'Could not load object with key {s3_key}') from ex

    def _write_blob_content(
        self,
        blob_id: BlobId,
        content: Content,
        write_callback: Optional[BytesWrittenCallback] = None
    ) -> Blob:
        s3_key = self._to_blob_s3_key(blob_id)

        with content.get_body() as body:
            self.aws_resources.blob_s3_bucket.upload_fileobj(
                Key=s3_key,
                Fileobj=body,
                ExtraArgs=dict(
                    ContentType=content.get_type()
                ),
                Callback=write_callback
            )
        s3_object = self.aws_resources.blob_s3_bucket.Object(s3_key)
        return Blob(
            blob_id=blob_id,
            content=S3ObjectContent(s3_object)
        )
