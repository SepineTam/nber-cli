import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from nber_cli import db
from nber_cli.core.models import NBERFeedItem
from nber_server.main import create_app
from nber_server.migrations import upgrade_database
from nber_server.routers.health import _package_version


def _client(db_path: Path):
    app = create_app(db_path=db_path, allowed_origins=["http://localhost:1420"])
    return TestClient(app)


def _insert_feed_item(db_path: Path, paper_id: str = "w12345") -> None:
    now = db._utc_now()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO feed_items (
                paper_id, title, authors_json, abstract, url, source_url, guid,
                first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                title = excluded.title,
                authors_json = excluded.authors_json,
                abstract = excluded.abstract,
                url = excluded.url,
                source_url = excluded.source_url,
                guid = excluded.guid,
                last_seen_at = excluded.last_seen_at
            """,
            (
                paper_id,
                "A Useful Paper",
                json.dumps(["Ada Lovelace", "Grace Hopper"]),
                "Feed abstract",
                f"https://www.nber.org/papers/{paper_id}",
                f"https://www.nber.org/papers/{paper_id}#rss",
                f"https://www.nber.org/papers/{paper_id}",
                now,
                now,
            ),
        )
        connection.commit()


def _insert_info_cache(db_path: Path, paper_id: str = "w12345") -> None:
    now = db._utc_now()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO info_cache (
                paper_id, title, authors_json, date, abstract, url,
                first_cached_at, last_fetched_at, fetch_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                "A Useful Paper",
                json.dumps(["Ada Lovelace", "Grace Hopper"]),
                "2026-07-08",
                "Detailed abstract",
                f"https://www.nber.org/papers/{paper_id}",
                now,
                now,
                0,
            ),
        )
        connection.commit()


def test_health_returns_status_and_database_path(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["db_path"] == str(db_path)


def test_health_version_falls_back_to_release_version(monkeypatch):
    def fail_version_lookup(package_name: str) -> str:
        raise RuntimeError(package_name)

    monkeypatch.setattr("nber_server.routers.health.get_version", fail_version_lookup)

    assert _package_version() == "0.11.0"


def test_upgrade_database_creates_read_status_and_records_revision(tmp_path):
    db_path = tmp_path / "nber.db"

    upgrade_database(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            )
        }
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert "read_status" in table_names
    assert revision == "20260708_0001"
    assert user_version == 3


def test_feed_returns_empty_list_for_empty_database(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        response = client.get("/api/v1/feed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["items"] == []
    assert payload["data"]["total_count"] == 0


def test_feed_includes_read_status_and_supports_unread_filter(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        _insert_feed_item(db_path, "w12345")
        db.set_paper_read_status(db_path, "w12345", True)

        all_response = client.get("/api/v1/feed")
        unread_response = client.get("/api/v1/feed?unread_only=true")

    assert all_response.status_code == 200
    assert all_response.json()["data"]["items"][0]["is_read"] is True
    assert unread_response.status_code == 200
    assert unread_response.json()["data"]["items"] == []


def test_refresh_feed_returns_counts_without_network(tmp_path, monkeypatch):
    db_path = tmp_path / "nber.db"

    def fake_fetch_feed(display_all=False, db_path=None, max_items=None):
        _insert_feed_item(Path(db_path), "w55555")
        return SimpleNamespace(
            new_count=1,
            total_fetched=1,
            items=[
                NBERFeedItem(
                    paper_id="w55555",
                    title="New Paper",
                    authors=[],
                    abstract="",
                    url="https://www.nber.org/papers/w55555",
                    source_url="https://www.nber.org/papers/w55555",
                    guid="https://www.nber.org/papers/w55555",
                )
            ],
        )

    monkeypatch.setattr("nber_server.routers.feed.fetch_feed", fake_fetch_feed)

    with _client(db_path) as client:
        response = client.post("/api/v1/feed/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["new_count"] == 1
    assert payload["data"]["total_count"] == 1
    assert payload["data"]["fetched_count"] == 1


def test_refresh_feed_maps_external_failure_to_503(tmp_path, monkeypatch):
    db_path = tmp_path / "nber.db"

    def fake_fetch_feed(display_all=False, db_path=None, max_items=None):
        raise OSError("network unavailable")

    monkeypatch.setattr("nber_server.routers.feed.fetch_feed", fake_fetch_feed)

    with _client(db_path) as client:
        response = client.post("/api/v1/feed/refresh")

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == 3
    assert "network unavailable" in payload["message"]


def test_paper_detail_reads_cache_and_marks_paper_read(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        _insert_feed_item(db_path, "w12345")
        _insert_info_cache(db_path, "w12345")

        response = client.get("/api/v1/papers/w12345")
        feed_response = client.get("/api/v1/feed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["paper_id"] == "w12345"
    assert payload["data"]["abstract"] == "Detailed abstract"
    assert payload["data"]["is_read"] is True
    assert feed_response.json()["data"]["items"][0]["is_read"] is True


def test_unknown_paper_returns_404(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        response = client.get("/api/v1/papers/w99999")

    assert response.status_code == 404
    assert response.json()["code"] == 1


def test_mark_read_can_toggle_status(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        response = client.post("/api/v1/papers/w12345/mark-read", json={"is_read": False})

    assert response.status_code == 200
    assert response.json()["data"] == {"paper_id": "w12345", "is_read": False}
    assert db.read_paper_read_status(db_path, "w12345") is False


def test_mark_read_toggle_is_reflected_in_feed(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        _insert_feed_item(db_path, "w12345")

        read_response = client.post("/api/v1/papers/w12345/mark-read", json={"is_read": True})
        read_feed = client.get("/api/v1/feed")

        unread_response = client.post("/api/v1/papers/w12345/mark-read", json={"is_read": False})
        unread_feed = client.get("/api/v1/feed")

        restored_response = client.post("/api/v1/papers/w12345/mark-read", json={"is_read": True})
        restored_feed = client.get("/api/v1/feed")

    assert read_response.json()["data"]["is_read"] is True
    assert read_feed.json()["data"]["items"][0]["is_read"] is True
    assert unread_response.json()["data"]["is_read"] is False
    assert unread_feed.json()["data"]["items"][0]["is_read"] is False
    assert restored_response.json()["data"]["is_read"] is True
    assert restored_feed.json()["data"]["items"][0]["is_read"] is True


def test_settings_get_and_patch(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        get_response = client.get("/api/v1/settings")
        patch_response = client.patch(
            "/api/v1/settings",
            json={"server_port": 32001, "feed_refresh_interval_minutes": 15},
        )

    assert get_response.status_code == 200
    assert get_response.json()["data"]["server_port"] == 31527
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["server_port"] == 32001
    assert patch_response.json()["data"]["feed_refresh_interval_minutes"] == 15


def test_settings_rejects_unknown_fields(tmp_path):
    db_path = tmp_path / "nber.db"

    with _client(db_path) as client:
        response = client.patch("/api/v1/settings", json={"db_path": "/tmp/other.db"})

    assert response.status_code == 422
    assert response.json()["code"] == 1
