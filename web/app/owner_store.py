"""Private owner dossier for the web process.

The repository intentionally contains no contact details. The web service reads
them from a JSON file outside the repository (``DREAMAI_OWNER_PROFILE``), and
only after the request has a valid owner cookie. A missing file means the
public assistant still knows its creator, but no private dossier exists yet.

The schema mirrors ``dream_ai/owner_profile.py`` so the CLI and web service can
share one private file without importing each other.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field, fields
from pathlib import Path

PROFILE_ENV = "DREAMAI_OWNER_PROFILE"
DEFAULT_PROFILE = Path.home() / ".dream_ai" / "owner-profile.json"
MAX_NOTES = 80
MAX_NOTE_CHARS = 1200


def profile_path() -> Path:
    raw = os.environ.get(PROFILE_ENV, "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_PROFILE


@dataclass
class OwnerProfile:
    name: str = "李贵江"
    latin: str = "Li Guijiang"
    gender: str = ""
    age: int = 0
    school: str = ""
    major: str = ""
    grade: str = ""
    duty: str = ""
    phone: str = ""
    wechat: str = ""
    qq: str = ""
    email_qq: str = ""
    email_gmail: str = ""
    email_foxmail: str = ""
    github: str = "Li-Guijiang"
    orcid: str = ""
    interests: list[str] = field(default_factory=list)
    situation: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: object) -> OwnerProfile:
        if not isinstance(raw, dict):
            return cls()
        values: dict[str, object] = {}
        for item in fields(cls):
            if item.name not in raw:
                continue
            value = raw[item.name]
            if item.name in {"interests", "situation", "notes"}:
                if isinstance(value, list):
                    values[item.name] = [str(part).strip() for part in value if str(part).strip()]
            elif item.name == "age":
                try:
                    values[item.name] = max(0, int(value))
                except (TypeError, ValueError):
                    values[item.name] = 0
            else:
                values[item.name] = str(value).strip()
        return cls(**values)

    def to_dict(self) -> dict[str, object]:
        return {item.name: getattr(self, item.name) for item in fields(self)}

    def contact_values(self) -> tuple[str, ...]:
        rough = (
            self.email_foxmail,
            self.email_gmail,
            self.email_qq,
            self.phone,
            self.wechat,
            self.qq,
        )
        return tuple(sorted({value for value in rough if value}, key=len, reverse=True))


def load_profile() -> OwnerProfile | None:
    path = profile_path()
    try:
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8-sig") as handle:
            return OwnerProfile.from_dict(json.load(handle))
    except (OSError, ValueError):
        return None


def save_profile(profile: OwnerProfile) -> Path:
    path = profile_path().expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def append_note(text: str) -> tuple[OwnerProfile, str]:
    fact = " ".join((text or "").split())[:MAX_NOTE_CHARS]
    if not fact:
        return load_profile() or OwnerProfile(), ""
    profile = load_profile() or OwnerProfile()
    if fact in profile.notes:
        return profile, fact
    profile.notes = [*profile.notes, fact][-MAX_NOTES:]
    save_profile(profile)
    return profile, fact


def clear_profile() -> Path | None:
    path = profile_path().expanduser()
    if not path.is_file():
        return None
    backup = path.with_name(f"{path.name}.{time.strftime('%Y%m%d-%H%M%S')}.bak")
    shutil.move(str(path), str(backup))
    try:
        backup.chmod(0o600)
    except OSError:
        pass
    return backup


def render_profile(profile: OwnerProfile | None, *, include_contacts: bool = True) -> str:
    if profile is None:
        return (
            "## 主人档案\n- 姓名：李贵江（Li Guijiang）\n"
            "- 私有档案尚未配置；身份规则仍然有效。"
        )
    lines = [
        "## 主人档案",
        f"- 姓名：{profile.name}（{profile.latin}）",
        (
            f"- 身份：{profile.gender}，{profile.age} 岁；"
            f"{profile.school}{profile.major}专业{profile.grade}学生，{profile.duty}"
        ),
        f"- 开源主页：GitHub {profile.github}" + (f"；{profile.orcid}" if profile.orcid else ""),
    ]
    if profile.interests:
        lines.append("- 爱好：" + "、".join(profile.interests))
    if profile.situation:
        lines.append("- 现状：" + "".join(profile.situation))
    if include_contacts:
        contacts = []
        if profile.phone:
            contacts.append(f"手机/微信 {profile.phone}")
        if profile.qq:
            contacts.append(f"QQ {profile.qq}")
        if profile.email_qq:
            contacts.append(f"QQ 邮箱 {profile.email_qq}")
        if profile.email_gmail:
            contacts.append(f"Gmail {profile.email_gmail}")
        if profile.email_foxmail:
            contacts.append(f"Foxmail {profile.email_foxmail}")
        if contacts:
            lines.append("- 联系方式（私密，未经本人同意不得对外提供）：" + "；".join(contacts))
    if profile.notes:
        lines.append("\n## 追加记忆")
        lines.extend(f"- {note}" for note in profile.notes)
    return "\n".join(lines)


COMMAND_SHOW = "查看我的全部档案"
COMMAND_UPDATE = "更新档案"
COMMAND_CLEAR = "清空档案"
COMMANDS = (COMMAND_SHOW, COMMAND_UPDATE, COMMAND_CLEAR)


def parse_command(text: str) -> tuple[str, str] | None:
    """Return ``(kind, payload)`` for an exact dossier command, else ``None``."""
    stripped = (text or "").strip()
    for opening, closing in (("【", "】"), ("[", "]")):
        if stripped.startswith(opening):
            end = stripped.find(closing, len(opening))
            if end == -1:
                return None
            name = stripped[len(opening) : end].strip()
            rest = stripped[end + 1 :].strip()
            break
    else:
        return None
    if name == COMMAND_SHOW:
        return "show", ""
    if name == COMMAND_CLEAR:
        return "clear", ""
    if name == COMMAND_UPDATE:
        return "update", rest
    return None


def mask_contacts(text: str, profile: OwnerProfile | None = None) -> str:
    if not text:
        return text
    profile = profile if profile is not None else load_profile()
    masked = text
    if profile is not None:
        for secret in profile.contact_values():
            masked = masked.replace(secret, "〔已隐藏〕")
    import re

    masked = re.sub(r"1[3-9]\d{9}", "〔已隐藏〕", masked)
    masked = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "〔已隐藏〕", masked)
    return masked

