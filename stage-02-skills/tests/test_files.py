"""File tools: đọc/ghi đúng phạm vi, lỗi có cấu trúc, chặn traversal/absolute/symlink escape."""

import json

import pytest

from reset_workspace import WorkspaceError, ensure_workspace, reset_workspace
from tools import list_files, read_file, write_file
from tools.files import MAX_READ_BYTES, _list, _read, _write


@pytest.fixture
def ws(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "data").mkdir(parents=True)
    (workspace / "output").mkdir()
    (workspace / "data" / "note.md").write_text("Xin chào", encoding="utf-8")
    return workspace


def test_read_ok(ws):
    assert _read(ws, "data/note.md") == {"ok": True, "path": "data/note.md", "content": "Xin chào"}


def test_read_missing_file(ws):
    result = _read(ws, "data/khong-ton-tai.md")
    assert result["ok"] is False and result["error"]["code"] == "FILE_NOT_FOUND"


@pytest.mark.parametrize("path", ["../secret.txt", "data/../../secret.txt"])
def test_read_traversal_blocked(ws, path):
    (ws.parent / "secret.txt").write_text("secret")
    assert _read(ws, path)["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_read_absolute_path_blocked(ws):
    assert _read(ws, str(ws / "data" / "note.md"))["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_read_symlink_escape_blocked(ws):
    (ws.parent / "secret.txt").write_text("secret")
    (ws / "data" / "link.txt").symlink_to(ws.parent / "secret.txt")
    result = _read(ws, "data/link.txt")
    assert result["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert "content" not in result


def test_read_too_large_and_non_utf8(ws):
    (ws / "data" / "big.txt").write_text("a" * (MAX_READ_BYTES + 1))
    (ws / "data" / "bin.dat").write_bytes(b"\xff\xfe\x00")
    assert _read(ws, "data/big.txt")["error"]["code"] == "FILE_TOO_LARGE"
    assert _read(ws, "data/bin.dat")["error"]["code"] == "NOT_UTF8_TEXT"
    assert _read(ws, "data")["error"]["code"] == "IS_A_DIRECTORY"


def test_write_created_then_updated(ws):
    first = _write(ws, "output/reports/summary.md", "# Tóm tắt")
    assert first == {"ok": True, "path": "output/reports/summary.md", "bytes": len("# Tóm tắt".encode()), "status": "created"}
    second = _write(ws, "output/reports/summary.md", "v2")
    assert second["status"] == "updated" and second["bytes"] == 2
    assert (ws / "output" / "reports" / "summary.md").read_text(encoding="utf-8") == "v2"


@pytest.mark.parametrize("path", ["data/note.md", "summary.md", "output", "output/../data/x.md", "../output/x.md"])
def test_write_outside_output_rejected(ws, path):
    result = _write(ws, path, "x")
    assert result["ok"] is False
    assert result["error"]["code"] in {"PATH_OUTSIDE_OUTPUT", "PATH_OUTSIDE_WORKSPACE"}
    assert (ws / "data" / "note.md").read_text(encoding="utf-8") == "Xin chào"


def test_write_absolute_and_symlink_escape_rejected(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (ws / "output" / "escape").symlink_to(outside, target_is_directory=True)
    assert _write(ws, str(ws / "output" / "a.md"), "x")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert _write(ws, "output/escape/a.md", "x")["ok"] is False
    assert list(outside.iterdir()) == []


def test_tools_return_json_against_project_workspace(lab_dirs):
    assert json.loads(read_file.invoke({"path": "data/weekly_notes.md"}))["ok"] is True
    written = json.loads(write_file.invoke({"path": "output/t.md", "content": "ok"}))
    assert written["status"] == "created"
    assert json.loads(read_file.invoke({"path": "output/t.md"}))["content"] == "ok"


def test_list_ok_sorted_and_single_level(ws):
    (ws / "data" / "b.md").write_text("B", encoding="utf-8")
    (ws / "data" / "a.md").write_text("A", encoding="utf-8")
    (ws / "data" / "sub").mkdir(exist_ok=True)
    (ws / "data" / "sub" / "inner.md").write_text("inner", encoding="utf-8")
    from tools.files import _list

    result = _list(ws, "data")
    assert result["ok"] is True and result["path"] == "data"
    names = [e["name"] for e in result["entries"]]
    assert names == sorted(names)
    by_name = {e["name"]: e for e in result["entries"]}
    assert by_name["a.md"] == {"name": "a.md", "path": "data/a.md", "type": "file"}
    assert by_name["sub"] == {"name": "sub", "path": "data/sub", "type": "directory"}
    # không duyệt đệ quy: inner.md không xuất hiện ở cấp data
    assert all(e["path"].count("/") == 1 for e in result["entries"])


def test_list_errors_for_file_missing_and_outside(ws):
    from tools.files import _list

    assert _list(ws, "data/note.md")["error"]["code"] == "NOT_A_DIRECTORY"
    assert _list(ws, "data/khong-ton-tai")["error"]["code"] == "FILE_NOT_FOUND"
    assert _list(ws, "../secret.txt")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert _list(ws, str(ws / "data"))["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_list_symlink_escape_blocked(ws, tmp_path):
    from tools.files import _list

    (tmp_path / "secret.txt").write_text("secret")
    (ws / "data" / "link.txt").symlink_to(tmp_path / "secret.txt")
    # liệt kê thư mục cha vẫn ok, nhưng đi vào symlink dẫn ra ngoài thì chặn
    assert _list(ws, "data")["ok"] is True
    result = _list(ws, "data/link.txt")
    assert result["ok"] is False and result["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_list_tool_registered_and_returns_json(lab_dirs):
    from tools import list_files

    assert list_files.name == "list_files"
    result = json.loads(list_files.invoke({"path": "data"}))
    assert result["ok"] is True and any(e["type"] in {"file", "directory"} for e in result["entries"])


def test_reset_restores_fixtures_and_requires_marker(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "data").mkdir(parents=True)
    (fixtures / "data" / "a.md").write_text("A")
    workspace = tmp_path / "workspace"
    ensure_workspace(workspace, fixtures)
    (workspace / "data" / "a.md").write_text("changed")
    (workspace / "output" / "r.md").write_text("R")
    ensure_workspace(workspace, fixtures)  # không ghi đè khi đã có workspace
    assert (workspace / "data" / "a.md").read_text() == "changed"
    reset_workspace(workspace, fixtures)
    assert (workspace / "data" / "a.md").read_text() == "A"
    assert list((workspace / "output").iterdir()) == []

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    with pytest.raises(WorkspaceError):
        reset_workspace(foreign, fixtures)
    with pytest.raises(WorkspaceError):
        ensure_workspace(foreign, fixtures)
    assert (foreign / "keep.txt").read_text() == "keep"
