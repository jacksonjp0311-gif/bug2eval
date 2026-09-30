import json
import sys
import os
from pathlib import Path

import pytest

from bug2eval.capture import capture_directories
from bug2eval.models import load_case
from bug2eval.runner import run_case, validate_case


@pytest.fixture
def guarded_case(tmp_path):
    before, after = tmp_path / 'before', tmp_path / 'after'
    for root, value in ((before, 0), (after, 42)):
        root.mkdir()
        (root / 'value.py').write_text(f'value = {value}\n')
        (root / 'verify.py').write_text('from value import value\nassert value == 42\n')
        (root / 'test_support').mkdir()
        (root / 'test_support/helper.py').write_text('expected = 42\n')
    case = capture_directories(before_dir=before, after_dir=after, output=tmp_path / 'case',
                               case_id='GUARD', title='value equals 42', verify_argv=[sys.executable, 'verify.py'])
    return load_case(case)


@pytest.mark.parametrize('attack', [
    "Path('verify.py').write_text('pass\\n')",
    "Path('verify.py').unlink()",
    "Path('verify.py').unlink(); Path('verify.py').mkdir()",
])
def test_verifier_tampering_cannot_pass(guarded_case, attack):
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', 'from pathlib import Path; '+attack], save_result=False)
    assert result['passed'] is False
    assert result['verifier_integrity']['intact'] is False
    assert result['verifier_integrity']['changed_paths']
    assert result['after_verify']['skipped'] is True


def test_tampered_verifier_is_not_executed(guarded_case, tmp_path):
    marker = tmp_path / 'executed'
    malicious = f'from pathlib import Path\nPath({str(marker)!r}).write_text("bad")\n'
    agent = f'from pathlib import Path; Path("verify.py").write_text({malicious!r})'
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', agent], save_result=False)
    assert not result['passed']
    assert not marker.exists()


def test_real_application_fix_still_passes(guarded_case):
    agent = "from pathlib import Path; Path('value.py').write_text('value = 42\\n')"
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', agent], save_result=False)
    assert result['passed']
    assert result['verifier_integrity']['intact']
    assert 'verify.py' in result['verifier_integrity']['protected_paths']


def test_explicit_protected_directory_catches_added_files(guarded_case):
    guarded_case.data['verification']['protected_paths'] = ['test_support']
    agent = "from pathlib import Path; Path('test_support/extra.py').write_text('pass\\n')"
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', agent], save_result=False)
    assert not result['passed']
    assert 'test_support/extra.py' in result['verifier_integrity']['changed_paths']


def test_verifier_must_be_identical_in_reference_snapshots(tmp_path):
    for name, script in [('before', 'raise SystemExit(1)\n'), ('after', 'pass\n')]:
        root = tmp_path / name
        root.mkdir()
        (root / 'verify.py').write_text(script)
    case_dir = capture_directories(before_dir=tmp_path/'before', after_dir=tmp_path/'after', output=tmp_path/'case',
                                   case_id='DIFFERENT', title='different tests', verify_argv=[sys.executable, 'verify.py'])
    result = validate_case(load_case(case_dir))
    assert not result['valid']
    assert any('verifier' in reason for reason in result['reasons'])


def test_missing_declared_protection_fails_closed(guarded_case):
    guarded_case.data['verification']['protected_paths'] = ['missing.py']
    from bug2eval.errors import CaseValidationError
    with pytest.raises(CaseValidationError, match='protected'):
        validate_case(guarded_case)


@pytest.mark.parametrize('paths', [[], ['../escape'], ['/absolute'], ['C:\\escape'], [4], 'verify.py'])
def test_malformed_protection_rejected(guarded_case, paths):
    guarded_case.data['verification']['protected_paths'] = paths
    (guarded_case.root/'metadata.json').write_text(json.dumps(guarded_case.data))
    from bug2eval.errors import CaseValidationError
    with pytest.raises(CaseValidationError):
        load_case(guarded_case.root)


def test_unknown_verifier_requires_explicit_protection(guarded_case):
    from bug2eval.errors import CaseValidationError
    guarded_case.data['verification']['argv'] = [sys.executable, '-c', 'from value import value; assert value == 42']
    with pytest.raises(CaseValidationError, match='--protect'):
        validate_case(guarded_case)


def test_capture_cli_records_protection(guarded_case, capsys):
    from bug2eval.cli import main
    from bug2eval.util import render_argv
    root = guarded_case.root.parent
    output = root / 'declared'
    assert main(['capture', '--id', 'DECLARED', '--title', 'declared protection',
                 '--before-dir', str(root/'before'), '--after-dir', str(root/'after'),
                 '--verify', render_argv(guarded_case.verify_argv), '--protect', 'test_support',
                 '--output', str(output), '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['validation']['valid']
    captured = load_case(output)
    assert captured.data['verification']['protected_paths'] == ['test_support']
    assert set(data['validation']['verifier_integrity']['protected_paths']) == {'test_support', 'verify.py'}


def test_cli_tampering_returns_failure_with_json_receipt(guarded_case, capsys):
    from bug2eval.cli import main
    from bug2eval.util import render_argv
    command = render_argv([sys.executable, '-c', "from pathlib import Path; Path('verify.py').write_text('pass\\n')"])
    assert main(['run', str(guarded_case.root), '--agent-cmd', command, '--json', '--no-save']) == 1
    receipt = json.loads(capsys.readouterr().out)
    assert not receipt['passed']
    assert receipt['after_verify']['skipped']
    assert receipt['after_verify']['exit_code'] is None


def test_symlink_replacement_is_rejected_even_with_identical_bytes(guarded_case, tmp_path):
    probe = tmp_path / 'probe-link'
    try:
        os.symlink('unused-target', probe)
    except OSError:
        pytest.skip('symlink creation is unavailable for this account')
    probe.unlink()
    code = "from pathlib import Path; import os; p=Path('verify.py'); Path('twin.py').write_bytes(p.read_bytes()); p.unlink(); os.symlink('twin.py', 'verify.py')"
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', code], save_result=False)
    assert not result['passed']
    assert result['after_verify']['skipped']


def test_pytest_discovery_protects_tests_and_configuration(guarded_case, tmp_path):
    from bug2eval.protection import protected_paths
    (tmp_path/'tests').mkdir()
    (tmp_path/'tests/test_value.py').write_text('pass\n')
    (tmp_path/'pytest.ini').write_text('[pytest]\n')
    guarded_case.data['verification']['argv'] = [sys.executable, '-m', 'pytest', '-q']
    assert set(protected_paths(guarded_case, tmp_path)) == {'tests', 'pytest.ini'}


def test_windows_relative_command_paths_are_inferred(guarded_case):
    from bug2eval.protection import protected_paths
    guarded_case.data['verification']['argv'] = [sys.executable, '.\\verify.py']
    assert protected_paths(guarded_case, guarded_case.root.parent/'before') == ['verify.py']


def test_timeout_is_not_valid_bug_evidence(guarded_case, monkeypatch):
    from bug2eval.util import CommandResult
    import bug2eval.runner as runner
    results = iter([CommandResult([], 124, '', '', 1, True), CommandResult([], 0, '', '', 0)])
    monkeypatch.setattr(runner, '_verification', lambda *args: next(results))
    result = runner.validate_case(guarded_case)
    assert not result['valid']
    assert any('timed out' in reason for reason in result['reasons'])


def test_prompt_path_does_not_disclose_reference_directory(guarded_case):
    code = "import os,sys;from pathlib import Path;p=Path(sys.argv[1]);assert p.parent.resolve()==Path.cwd().resolve();assert Path(os.environ['BUG2EVAL_PROMPT_FILE'])==p;assert not (p.parent/'workspace_after.tar.gz').exists();Path('value.py').write_text('value = 42\\n')"
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', code, '{prompt_file}'], save_result=False)
    assert result['passed']
    assert str(guarded_case.root) not in str(result['agent']['argv'])


def test_agent_nonzero_exit_cannot_be_counted_as_solve(guarded_case):
    code = "from pathlib import Path;Path('value.py').write_text('value = 42\\n');raise SystemExit(7)"
    result = run_case(guarded_case, agent_argv=[sys.executable, '-c', code], save_result=False)
    assert result['after_verify']['exit_code'] == 0
    assert not result['passed']
