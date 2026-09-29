from bug2eval.cli import main


def test_init(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".bug2eval" / "config.json").is_file()
