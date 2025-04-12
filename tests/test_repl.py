from snagit import repl
from snagit.core import execute_code


def execute_program(code, contents=""):
    return execute_code(code, contents, exec_class=repl.Repl)


def test_repl(capsys):
    def _inputs():
        yield ""
        yield "quit"
        yield "?"
        raise KeyboardInterrupt("")

    inputs = _inputs()

    def input_handler(prompt, history=None):
        return next(inputs)

    r = repl.Repl(input_handler=input_handler)
    assert str(r.repl(print_all=True, history=None)) == ""
    assert str(r.repl(history=None)) == ""


def test_help(capsys):
    text = execute_program("help")
    captured = capsys.readouterr()
    assert "Commands" in captured.out
    assert not text

    text = execute_program("help help")
    captured = capsys.readouterr()
    assert "Display help on available commands" in captured.out
    assert not text

    text = execute_program("help ----")
    captured = capsys.readouterr()
    assert "Unknown command ----" in captured.out
    assert not text


def test_list(capsys):
    interp = repl.Repl()
    interp.execute("help\nhelp\nhelp")
    captured = capsys.readouterr()

    interp.execute("list")
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 3


def test_load(mocked_example):
    domain = "https://example.com"
    text = execute_program(f"load {domain}")
    assert "Example Domain" in text

    try:
        text = execute_program("load foo")
    except Exception:
        pass
    else:
        assert False, "No exception thrown"


def test_load_all(mocked_httpbin):
    keys = [k for k, v in mocked_httpbin]
    data = [v for k, v in mocked_httpbin]
    text = execute_program("load_all", keys)
    assert text == "\n".join(data)


def test_parse_line(capsys):
    execute_program('parse_line a b "c d" x=9')
    captured = capsys.readouterr().out
    assert "'a', 'b', 'c d'" in captured
    assert "'x': 9" in captured


def test_print(capsys):
    execute_program("print", "foobar")
    assert "foobar" == capsys.readouterr().out.strip()


def test_cache():
    interp = repl.Repl()
    interp.execute("cache")
    assert interp.loader.use_cache is True


def test_debug():
    interp = repl.Repl()
    interp.execute("debug")
    assert interp.do_debug is True


def test_end():
    contents = "a b c".split()
    interp = repl.Repl(contents)
    try:
        interp.execute("end")
    except Exception:
        assert False

    interp.execute("merge")
    assert len(interp.contents.stack) == 1

    interp.execute("end")
    assert len(interp.contents.stack) == 0


def test_run():
    assert "Hello, world" == execute_program("run tests/script.snagit", "Hello, world#")


def test_execute_script():
    r = repl.Repl()
    assert "Hello, world" == str(r.execute_script("tests/script.snagit", "Hello, world#"))
