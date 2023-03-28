from io import BytesIO
from typing import Callable, Type, TypeVar

from sbs2 import BlobId, Content, ContentBody, ContentLength, ContentType

InType = TypeVar('InType')
OutType = TypeVar('OutType')


def patch_equals_key(target_type: Type[InType], eq_key_func: Callable[[InType], OutType]) -> None:
    def eq(self, other) -> bool:
        return type(other) == target_type and eq_key_func(self) == eq_key_func(other)
    target_type.__eq__ = eq


class WriteCounter:
    def __init__(self) -> None:
        super().__init__()
        self.writes = 0

    def __call__(self, *args, **kwargs) -> None:
        self.writes += 1


class _InlinePngContent(Content):
    def __init__(self, content_body: bytes) -> None:
        self.content_body = content_body

    def get_type(self) -> ContentType:
        return ContentType('image/png')

    def get_body(self) -> ContentBody:
        return BytesIO(self.content_body)

    def get_length(self) -> ContentLength:
        return len(self.content_body)


red_png_content: Content = _InlinePngContent(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x02\x00\x00\x00Km)\xdc\x00\x00\x00\x01s'
    b'RGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e\xc3\x00'
    b'\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00\x00\x12IDAT\x18Wcx+\xa3\x82\x15\r)\t\x19\x15\x00\x99\xbbKAF\xf6\xeb\x1b\x00'
    b'\x00\x00\x00IEND\xaeB`\x82'
)
green_png_content: Content = _InlinePngContent(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x06\x00\x00\x00\xc4\x0f\xbe\x8b\x00\x00'
    b'\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e'
    b'\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x17IDAT(Scd\xf8\x0f\x84x\x00\x13\x94\xc6\t\x86\x83\x02\x06\x06'
    b'\x00\x11\\\x02\x0e\x9c\x0c \x18\x00\x00\x00\x00IEND\xaeB`\x82'
)
blue_png_content: Content = _InlinePngContent(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x06\x00\x00\x00\xc4\x0f\xbe\x8b\x00\x00"
    b"\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e"
    b"\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00\x00'IDAT(S}\xc8\xa1\r\x000\x10\xc4\xb0\xdb\x7f\xe9\x14\xbd\x14\x10\x15"
    b"\x98x\x1b\xfceZ\xa6eZ\xa6eZ\xa6e\x1exCW\x7f\x81\xf1\x0e;g\x00\x00\x00\x00IEND\xaeB`\x82"
)
white_png_content: Content = _InlinePngContent(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x06\x00\x00\x00\xc4\x0f\xbe\x8b\x00\x00'
    b'\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e'
    b'\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x17IDAT(Sc\xfc\x0f\x04\x0cx\x00\x13\x94\xc6\t\x86\x83\x02\x06'
    b'\x06\x00\x1bn\x04\x0csL\x0f\xa6\x00\x00\x00\x00IEND\xaeB`\x82'
)
black_png_content: Content = _InlinePngContent(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x06\x00\x00\x00\xc4\x0f\xbe\x8b\x00\x00'
    b'\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e'
    b'\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x19IDAT(Scd``\xf8\x0f\xc48\x01\x13\x94\xc6\t\x86\x83\x02\x06'
    b'\x06\x00\x0cS\x01\x0f\xbb\xb9En\x00\x00\x00\x00IEND\xaeB`\x82'
)
red_png_blob_id = BlobId('feb78a44d55c9169801cf606cd6041ad9a5f69c9.png')
green_png_blob_id = BlobId('1a1779bf090faccd182900ff292b8a713b23bf52.png')
blue_png_blob_id = BlobId('872f563751d7e5127dd99ac99cdbb24f33374664.png')
white_png_blob_id = BlobId('25db94b2a2ba54812cb25602e4badc562395a415.png')
black_png_blob_id = BlobId('67f5f00c34e2c219b7d6537fa74e6531a61fdea3.png')
