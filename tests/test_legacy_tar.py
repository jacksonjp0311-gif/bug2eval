import io
import tarfile

import pytest

from bug2eval.archive import safe_extract_tar
from bug2eval.errors import CaseValidationError


@pytest.fixture
def legacy_tar(monkeypatch):
    original = tarfile.TarFile.extractall
    has_filter = hasattr(tarfile, 'data_filter')
    monkeypatch.delattr(tarfile, 'data_filter', raising=False)

    def legacy_extractall(self, path='.', members=None, *, numeric_owner=False):
        # Deliberately no filter keyword, matching Python 3.10.11.
        kwargs = {'filter': 'fully_trusted'} if has_filter else {}
        return original(self, path, members, numeric_owner=numeric_owner, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, 'extractall', legacy_extractall)


def test_legacy_regular_file(tmp_path, legacy_tar):
    archive = tmp_path / 'regular.tar.gz'
    with tarfile.open(archive, 'w:gz') as tf:
        entry = tarfile.TarInfo('folder/value.txt')
        entry.size = 2
        tf.addfile(entry, io.BytesIO(b'42'))
    safe_extract_tar(archive, tmp_path / 'out')
    assert (tmp_path / 'out/folder/value.txt').read_bytes() == b'42'


@pytest.mark.parametrize('kind', ['traversal', 'symlink', 'hardlink', 'fifo'])
def test_legacy_rejects_unsafe_members(tmp_path, legacy_tar, kind):
    archive = tmp_path / 'unsafe.tar.gz'
    with tarfile.open(archive, 'w:gz') as tf:
        entry = tarfile.TarInfo('../escape' if kind == 'traversal' else 'link')
        if kind in ('symlink', 'hardlink'):
            entry.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
            entry.linkname = '../escape'
        elif kind == 'fifo':
            entry.type = tarfile.FIFOTYPE
        tf.addfile(entry)
    with pytest.raises(CaseValidationError):
        safe_extract_tar(archive, tmp_path / 'out')
    assert not (tmp_path / 'escape').exists()
