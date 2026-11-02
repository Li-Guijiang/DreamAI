"""Private owner dossier.

The dossier is deliberately stored *outside* the repository and outside the
served web root. The public source tree only knows the schema, never the
contact values. A missing file simply means "private details are not set yet";
the identity rules in :mod:`dream_ai.identity` still work.

The file is JSON so both the CLI and the web service can read it without an
extra dependency::

    {
      "name": "李贵江",
      "latin": "Li Guijiang",
      "gender": "男",
      "age": 19,
      "school": "...",
      "major": "...",
      "grade": "大二",
      "duty": "班长",
      "phone": "...",
      "wechat": "...",
      "qq": "...",
      "email_qq": "...",
      "email_gmail": "...",
      "email_foxmail": "...",
      "github": "Li-Guijiang",
      "orcid": "ORCID 国际研究者",
      "interests": ["..."],
      "situation": ["..."],
      "notes": ["..."]
    }
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
    """Everything private the owner asked Dream AI to remember."""

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
        """Contact strings in longest-first order, for exact masking."""
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
    """Read the dossier, or return ``None`` when it has not been provisioned."""
    path = profile_path()
    try:
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8-sig") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return None
    return OwnerProfile.from_dict(raw)


def _assert_private_location(path: Path) -> None:
    """Refuse to write a dossier inside this checkout or the served web tree."""
    resolved = path.resolve()
    repository = Path(__file__).resolve().parents[1]
    if repository in resolved.parents or resolved == repository:
        raise ValueError("owner profile must live outside the repository")
    if "web" in resolved.parts and (repository / "web") in resolved.parents:
        raise ValueError("owner profile must not live under the served web directory")


def save_profile(profile: OwnerProfile) -> Path:
    """Write the dossier atomically with owner-only permissions."""
    path = profile_path().expanduser()
    _assert_private_location(path)
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
    """Append one owner-authored fact, keeping the dossier bounded."""
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
    """Archive and remove the private dossier; identity rules remain public."""
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
    """Render the dossier for the owner command and owner-only prompts."""
    if profile is None:
        return "## 主人档案\n- 姓名：李贵江（Li Guijiang）\n- 私有档案尚未配置；身份规则仍然有效。"
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
