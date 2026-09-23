"""
MD2WX 通用环境变量与 .env 读取工具 (纯标准库，零第三方依赖)

统一为 CLI 提供环境变量加载能力：优先读取进程环境变量 os.environ，
其次按优先级回退到常见 .env 路径（当前目录 > ~/.config/md2wx > 项目根目录）。
"""
import os
from pathlib import Path
from typing import Dict, List, Optional

# 占位符前缀：示例配置中的 your_xxx / <xxx> 一律视为"未配置"
_PLACEHOLDER_PREFIXES = ("your_", "<")


def candidate_env_paths() -> List[Path]:
    """按优先级返回候选 .env 文件路径（越靠前优先级越高）"""
    return [
        Path.cwd() / ".env",
        Path.home() / ".config" / "md2wx" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]


def is_placeholder(value: Optional[str]) -> bool:
    """判断配置值是否为空或示例占位符（视为未配置）"""
    if value is None:
        return True
    v = value.strip()
    if not v:
        return True
    return v.startswith(_PLACEHOLDER_PREFIXES)


def _parse_env_line(line: str):
    """解析单行 KEY=VALUE，兼容 export 前缀、注释与引号包裹"""
    line = line.strip()
    if line.startswith("export "):
        line = line[len("export "):].strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, val = line.split("=", 1)
    val = val.strip().strip("'\"")
    if is_placeholder(val):
        return None
    return key.strip(), val


def read_env_file(path: Path) -> Dict[str, str]:
    """读取单个 .env 文件为字典（utf-8-sig 兼容 BOM，自动跳过占位符）"""
    result: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                parsed = _parse_env_line(line)
                if parsed:
                    result[parsed[0]] = parsed[1]
    except OSError:
        pass
    return result


def load_env(keys: Optional[List[str]] = None) -> Dict[str, str]:
    """
    合并 os.environ 与候选 .env 文件，os.environ 优先级最高。
    keys 为 None 时返回全部键值；否则仅返回指定键中已配置的项。
    """
    merged: Dict[str, str] = {}
    for path in candidate_env_paths():
        if not path.exists():
            continue
        for key, val in read_env_file(path).items():
            merged.setdefault(key, val)
    for key, val in os.environ.items():
        if not is_placeholder(val):
            merged[key] = val

    if keys is None:
        return merged
    return {k: merged[k] for k in keys if k in merged}
