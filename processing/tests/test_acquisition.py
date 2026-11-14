from unittest.mock import patch

import numpy as np
import pytest

from processing.scripts.acquire_salda_jezero import fetch, crop_mola, verify_mola_label


class Response:
    def __init__(self, data=b'ab', status=206, content_range='bytes 2-3/10'):
        self.data, self.status = data, status
        self.headers = {'Content-Range': content_range, 'Content-Length': str(len(data)), 'ETag': 'test'}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


def test_exact_range_request_and_sha():
    with patch('urllib.request.urlopen', return_value=Response()) as open_url:
        data, meta = fetch('https://example.invalid/x', byte_range=(2, 3), limit=10)
    assert data == b'ab'
    assert open_url.call_args.args[0].headers['Range'] == 'bytes=2-3'
    assert len(meta['sha256']) == 64 and meta['content_range'] == 'bytes 2-3/10'


@pytest.mark.parametrize('response', [Response(status=200), Response(content_range='bytes 3-4/10'),
                                      Response(data=b'a'), Response(data=b'abc')])
def test_invalid_range_response_is_rejected(response):
    with patch('urllib.request.urlopen', return_value=response):
        with pytest.raises(ValueError):
            fetch('https://example.invalid/x', byte_range=(2, 3), limit=10)


def test_download_size_limit():
    with patch('urllib.request.urlopen', return_value=Response(data=b'abc', status=200)):
        with pytest.raises(ValueError, match='limit'):
            fetch('https://example.invalid/x', limit=2)


def test_big_endian_crop_preserves_zero_and_grid_corners():
    data = np.zeros((2, 11520), dtype='>i2')
    data[0, 9800:9803] = [-3000, 0, 100]
    crop, transform = crop_mola(data.tobytes(), 3200, 3202, 9800, 9803)
    assert crop.tolist() == [[-3000, 0, 100], [0, 0, 0]]
    assert transform @ (0, 0) == (9800/128, 19)
    assert transform @ (3, 2) == (9803/128, 19-2/128)
    assert transform @ (.5, .5) == ((9800+.5)/128, 19-.5/128)


def test_unexpected_label_rejected():
    with pytest.raises(ValueError, match='Unexpected'):
        verify_mola_label('NAME = RADIUS')
