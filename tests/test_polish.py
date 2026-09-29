import copy
import json
import sys
from pathlib import Path

import pytest

from bug2eval.archive import pack_case, unpack_case
from bug2eval.capture import capture_directories
from bug2eval.cli import main
from bug2eval.errors import CaseValidationError
from bug2eval.models import load_case
from bug2eval.runner import run_case
from bug2eval.util import run_command


@pytest.fixture
def case_dir(tmp_path):
    before, after = tmp_path / 'before', tmp_path / 'after'
    for root, value in ((before, 0), (after, 42)):
        root.mkdir()
        (root / 'value.py').write_text(f'value = {value}\n', encoding='utf-8')
        (root / 'verify.py').write_text('from value import value\nassert value == 42\n', encoding='utf-8')
    return capture_directories(before_dir=before, after_dir=after, output=tmp_path / 'CASE',
                               case_id='CASE', title='value must be 42', verify_argv=[sys.executable, 'verify.py'])


@pytest.mark.parametrize('change', [
    lambda d: [],
    lambda d: dict(d, verification=None),
    lambda d: dict(d, verification={'argv': [], 'timeout_sec': 1}),
    lambda d: dict(d, verification={'argv': [7], 'timeout_sec': 1}),
    lambda d: dict(d, verification={'argv': ['python'], 'timeout_sec': 0}),
    lambda d: dict(d, artifacts={}),
    lambda d: dict(d, case_id='../outside'),
    lambda d: dict(d, expected={'before': 'pass', 'after': 'pass', 'verify_exit_code': 0}),
])
def test_invalid_metadata_is_rejected(case_dir, change):
    path = case_dir / 'metadata.json'
    path.write_text(json.dumps(change(json.loads(path.read_text()))), encoding='utf-8')
    with pytest.raises(CaseValidationError):
        load_case(case_dir)


@pytest.mark.parametrize('path', ['../outside.txt', '/absolute.txt', 'C:\\outside.txt', '..\\outside.txt'])
def test_artifact_paths_stay_inside_case(case_dir, path):
    metadata = case_dir / 'metadata.json'
    data = json.loads(metadata.read_text())
    data['artifacts']['prompt']['path'] = path
    metadata.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(CaseValidationError):
        load_case(case_dir)


def test_already_passing_case_is_not_an_agent_success(case_dir):
    data_path = case_dir / 'metadata.json'
    data = json.loads(data_path.read_text())
    data['artifacts']['before'] = copy.deepcopy(data['artifacts']['after'])
    data_path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(CaseValidationError, match='already passes'):
        run_case(load_case(case_dir), agent_argv=None, save_result=False)


def test_broken_reference_is_rejected_before_running_agent(case_dir, tmp_path):
    data_path = case_dir / 'metadata.json'
    data = json.loads(data_path.read_text())
    data['artifacts']['after'] = copy.deepcopy(data['artifacts']['before'])
    data_path.write_text(json.dumps(data), encoding='utf-8')
    marker = tmp_path / 'agent-ran'
    with pytest.raises(CaseValidationError, match='reference fix'):
        run_case(load_case(case_dir), agent_argv=[sys.executable, '-c', f'open({str(marker)!r}, "w").close()'], save_result=False)
    assert not marker.exists()


def test_capture_cannot_replace_source(case_dir):
    source = case_dir.parent / 'before'
    original = (source / 'value.py').read_bytes()
    with pytest.raises(ValueError, match='overlap'):
        capture_directories(before_dir=source, after_dir=case_dir.parent / 'after',
                            output=source, force=True, case_id='unsafe', title='unsafe', verify_argv=['python'])
    assert (source / 'value.py').read_bytes() == original


def test_corrupt_unpack_preserves_existing_case(case_dir, tmp_path):
    archive = tmp_path / 'broken.b2e'
    archive.write_bytes(b'not a ZIP')
    original = (case_dir / 'metadata.json').read_bytes()
    assert main(['unpack', str(archive), '--output', str(case_dir), '--force']) == 3
    assert (case_dir / 'metadata.json').read_bytes() == original


def test_case_validation_exit_code_and_json(tmp_path, capsys):
    (tmp_path / 'metadata.json').write_text('{}')
    assert main(['validate', str(tmp_path), '--json']) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)['error']
    assert 'Traceback' not in output.err


def test_packed_results_do_not_overwrite(case_dir, tmp_path, monkeypatch):
    archive = pack_case(case_dir, tmp_path / 'case.b2e')
    monkeypatch.chdir(tmp_path)
    # Pin the timestamp to reproduce collisions independently of machine speed.
    import bug2eval.cli as cli
    class FixedTime:
        @classmethod
        def now(cls, tz):
            return cls()
        def strftime(self, pattern):
            return '20260929T000000Z'
    monkeypatch.setattr(cli, 'datetime', FixedTime)
    for _ in range(2):
        assert main(['run', str(archive)]) == 1
    assert len(list((tmp_path / '.bug2eval/results').glob('*.json'))) == 2


def test_timeout_preserves_partial_output(tmp_path):
    result = run_command([sys.executable, '-c', 'import time; print("diagnostic", flush=True); time.sleep(10)'], cwd=tmp_path, timeout=1)
    assert result.timed_out
    assert 'diagnostic' in result.stdout


def test_unpack_valid_case_and_replace_valid_destination(case_dir, tmp_path):
    archive = pack_case(case_dir, tmp_path / 'valid.b2e')
    destination = tmp_path / 'unpacked'
    assert unpack_case(archive, destination) == destination
    assert load_case(destination).case_id == 'CASE'
    (destination / 'old.txt').write_text('old content')
    unpack_case(archive, destination, force=True)
    assert not (destination / 'old.txt').exists()
    assert load_case(destination).case_id == 'CASE'


def test_unpack_cannot_replace_unrelated_folder(case_dir, tmp_path):
    archive = pack_case(case_dir, tmp_path / 'valid.b2e')
    destination = tmp_path / 'unrelated'
    destination.mkdir()
    marker = destination / 'important.txt'
    marker.write_text('keep')
    with pytest.raises(CaseValidationError):
        unpack_case(archive, destination, force=True)
    assert marker.read_text() == 'keep'


def test_capture_rejects_nested_output_before_writing(case_dir):
    source = case_dir.parent / 'before'
    output = source / 'nested'
    with pytest.raises(ValueError, match='overlap'):
        capture_directories(before_dir=source, after_dir=case_dir.parent / 'after',
                            output=output, case_id='nested', title='nested', verify_argv=['python'])
    assert not output.exists()


def test_metadata_bad_json_is_a_case_error(tmp_path, capsys):
    (tmp_path / 'metadata.json').write_text('{')
    assert main(['inspect', str(tmp_path), '--json']) == 2
    assert 'invalid metadata' in json.loads(capsys.readouterr().out)['error']


def test_failed_capture_preserves_previous_case(case_dir):
    original = (case_dir / 'metadata.json').read_bytes()
    with pytest.raises(ValueError, match='max size'):
        capture_directories(before_dir=case_dir.parent / 'before', after_dir=case_dir.parent / 'after',
                            output=case_dir, force=True, case_id='CASE', title='replacement',
                            verify_argv=['python', 'verify.py'], max_bytes=1)
    assert (case_dir / 'metadata.json').read_bytes() == original
    assert load_case(case_dir).title == 'value must be 42'


def test_successful_capture_replaces_previous_case(case_dir):
    result = capture_directories(before_dir=case_dir.parent / 'before', after_dir=case_dir.parent / 'after',
                                 output=case_dir, force=True, case_id='CASE', title='replacement',
                                 verify_argv=[sys.executable, 'verify.py'])
    assert result == case_dir
    assert load_case(case_dir).title == 'replacement'
