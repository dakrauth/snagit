import pytest
from snagit.__main__ import run_program


def test_help(capsys):
    with pytest.raises(SystemExit):
        run_program(["--help"])

    captured = capsys.readouterr()
    assert "Enter interactive (REPL) script mode" in captured.out


def test_repl_help(capsys):
    content = run_program("--exec help".split())
    assert "Commands" in capsys.readouterr().out
