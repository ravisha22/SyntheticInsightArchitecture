"""Authentication and anti-bot middleware for SIA dashboard."""
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SIAAuth:
    """Handles daily password rotation, login tracking, and lockout."""

    def __init__(self, storage_path: str = "auth_state.json"):
        self.storage_path = Path(storage_path)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.storage_path.exists():
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        return {"failed_attempts": {}, "daily_passwords": {}, "magic_links": {}}

    def _save_state(self):
        self.storage_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def generate_daily_password(self) -> str:
        """Generate a 24-char special-characters-only password for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today in self.state.get("daily_passwords", {}):
            return self.state["daily_passwords"][today]

        special = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
        password = "".join(secrets.choice(special) for _ in range(24))
        self.state.setdefault("daily_passwords", {})[today] = password
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        self.state["daily_passwords"] = {
            key: value
            for key, value in self.state["daily_passwords"].items()
            if key >= cutoff
        }
        self._save_state()
        return password

    def check_lockout(self, ip: str) -> bool:
        """Return True if IP is locked out (5+ failures in last 4 hours)."""
        attempts = self.state.get("failed_attempts", {}).get(ip, [])
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
        recent = [attempt for attempt in attempts if attempt > cutoff]
        return len(recent) >= 5

    def record_failure(self, ip: str):
        """Record a failed login attempt."""
        self.state.setdefault("failed_attempts", {}).setdefault(ip, [])
        self.state["failed_attempts"][ip].append(datetime.now(timezone.utc).isoformat())
        self._save_state()

    def generate_magic_link(self, base_url: str) -> str:
        """Generate a single-use magic login link."""
        token = secrets.token_urlsafe(32)
        self.state.setdefault("magic_links", {})[token] = {
            "created": datetime.now(timezone.utc).isoformat(),
            "used": False,
        }
        self._save_state()
        return f"{base_url}?token={token}"

    def validate_magic_link(self, token: str) -> bool:
        """Validate and consume a magic link."""
        link = self.state.get("magic_links", {}).get(token)
        if not link or link.get("used"):
            return False
        created = datetime.fromisoformat(link["created"])
        if datetime.now(timezone.utc) - created > timedelta(minutes=15):
            return False
        link["used"] = True
        self._save_state()
        return True

    def validate_password(self, password: str) -> bool:
        """Check if password matches today's or yesterday's password."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        return password in [
            self.state.get("daily_passwords", {}).get(today, ""),
            self.state.get("daily_passwords", {}).get(yesterday, ""),
        ]
