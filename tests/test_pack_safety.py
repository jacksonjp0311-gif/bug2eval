from pathlib import Path
from unittest.mock import patch
import zipfile

import pytest

from bug2eval.archive import pack_case
from bug2eval.errors import CaseValidationError
from test_polish import case_dir


@pytest.mark.parametrize('target', ['metadata.json', 'prompt.md', 'artifacts/workspace_before.tar.gz', 'README.md'])
def test_pack_cannot_overwrite_case_files(case_dir, target):
    output = case_dir / target
    original = output.read_bytes()
    with pytest.raises((ValueError, CaseValidationError)):
        pack_case(case_dir, output)
    assert output.read_bytes() == original


def test_declared_artifact_with_b2e_suffix_is_protected(case_dir):
    import json
    meta = case_dir / 'metadata.json'
    data = json.loads(meta.read_text())
    original_path = case_dir / data['artifacts']['before']['path']
    target = case_dir / 'source.b2e'
    original_path.rename(target)
    data['artifacts']['before']['path'] = 'source.b2e'
    meta.write_text(json.dumps(data))
    original = target.read_bytes()
    with pytest.raises((ValueError, CaseValidationError)):
        pack_case(case_dir, target)
    assert target.read_bytes() == original


@pytest.mark.parametrize('failure', ['write', 'replace'])
def test_pack_failure_preserves_previous_archive(case_dir, tmp_path, failure):
    output = pack_case(case_dir, tmp_path / 'case.b2e')
    original = output.read_bytes()
    target = zipfile.ZipFile if failure == 'write' else Path
    with patch.object(target, failure, side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            pack_case(case_dir, output)
    assert output.read_bytes() == original


def test_repeated_internal_pack_excludes_itself_and_staging(case_dir):
    output = case_dir / 'bundle.b2e'
    for _ in range(2):
        pack_case(case_dir, output)
        with zipfile.ZipFile(output) as zf:
            assert 'metadata.json' in zf.namelist()
            assert 'bundle.b2e' not in zf.namelist()
            assert not any('.bug2eval-pack-' in name for name in zf.namelist())
