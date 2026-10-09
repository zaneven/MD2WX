"""MD2WX 环境变量与 .env 读取工具单元测试"""
from pathlib import Path

from md2wx import envutil
from md2wx.envutil import (
    candidate_env_paths,
    is_placeholder,
    load_env,
    read_env_file,
    _parse_env_line,
)


def test_is_placeholder():
    assert is_placeholder(None)
    assert is_placeholder("")
    assert is_placeholder("  ")
    assert is_placeholder("your_appid_here")
    assert is_placeholder("<APP_ID>")
    assert not is_placeholder("wx1234567890")
    assert not is_placeholder("your" + "x")  # 前缀 your_ 才算占位


def test_parse_env_line_variants():
    assert _parse_env_line("KEY=value") == ("KEY", "value")
    assert _parse_env_line("export KEY=value") == ("KEY", "value")
    assert _parse_env_line('KEY="quoted value"') == ("KEY", "quoted value")
    assert _parse_env_line("KEY='sq'") == ("KEY", "sq")
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("no equals sign") is None
    assert _parse_env_line("EMPTY=") is None  # 空值视为未配置
    assert _parse_env_line("KEY=your_placeholder") is None


def test_read_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "A=1\n# 注释\nB=\"two words\"\nC=your_x\n",
        encoding="utf-8",
    )
    data = read_env_file(env_file)
    assert data == {"A": "1", "B": "two words"}


def test_read_env_file_missing_returns_empty(tmp_path):
    assert read_env_file(tmp_path / "not-exist.env") == {}


def test_load_env_os_environ_wins(tmp_path, monkeypatch):
    """进程环境变量优先级高于 .env 文件"""
    f1 = tmp_path / "a.env"
    f1.write_text("WECHAT_APP_ID=file_id\nSHARED=file\n", encoding="utf-8")
    monkeypatch.setattr(envutil, "candidate_env_paths", lambda: [f1])
    monkeypatch.setenv("WECHAT_APP_ID", "env_id")
    monkeypatch.setenv("SHARED", "env")

    merged = load_env()
    assert merged["WECHAT_APP_ID"] == "env_id"
    assert merged["SHARED"] == "env"


def test_load_env_priority_order(tmp_path, monkeypatch):
    """候选路径越靠前优先级越高 (setdefault 语义)"""
    f1 = tmp_path / "high.env"
    f2 = tmp_path / "low.env"
    f1.write_text("K=high\n", encoding="utf-8")
    f2.write_text("K=low\nONLY_LOW=1\n", encoding="utf-8")
    monkeypatch.setattr(envutil, "candidate_env_paths", lambda: [f1, f2])
    monkeypatch.setattr(envutil.os, "environ", {})

    merged = load_env()
    assert merged["K"] == "high"
    assert merged["ONLY_LOW"] == "1"


def test_load_env_keys_filter(tmp_path, monkeypatch):
    f1 = tmp_path / "a.env"
    f1.write_text("A=1\nB=2\n", encoding="utf-8")
    monkeypatch.setattr(envutil, "candidate_env_paths", lambda: [f1])
    monkeypatch.setattr(envutil.os, "environ", {})

    assert load_env(keys=["A"]) == {"A": "1"}
    assert load_env(keys=["MISSING"]) == {}


def test_candidate_env_paths_shape():
    paths = candidate_env_paths()
    assert all(isinstance(p, Path) for p in paths)
    assert len(paths) >= 2
