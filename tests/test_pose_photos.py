"""
Tests for the per-pose reference photograph contract (GET /api/pose-photos).

The endpoint reports only photo files that genuinely exist in
static/images/poses/, so the frontend never renders a photo that is
not there. These tests verify the empty-directory contract, the
discovery of a dropped-in photo file, and the filename allowlist.
"""

import pytest
from pathlib import Path
from web_app import app, POSE_PHOTO_BASENAMES, POSE_PHOTO_EXTENSIONS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _poses_dir():
    return Path(app.static_folder) / "images" / "poses"


class TestPosePhotosEndpoint:
    def test_response_shape(self, client):
        resp = client.get("/api/pose-photos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert isinstance(data["photos"], dict)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["photos"])

    def test_only_existing_files_listed(self, client):
        """Every returned URL must resolve to a real file (no phantom photos)."""
        data = client.get("/api/pose-photos").get_json()
        for pose_id, url in data["photos"].items():
            assert pose_id in {str(k) for k in POSE_PHOTO_BASENAMES}
            rel = url.replace("/static/", "", 1)
            assert (_poses_dir().parent.parent / rel).is_file(), url

    def test_discovers_dropped_in_photo(self, client):
        """A photo file added under the contracted basename is discovered."""
        target = _poses_dir() / f"{POSE_PHOTO_BASENAMES[3]}{POSE_PHOTO_EXTENSIONS[0]}"
        created = False
        if not target.is_file():
            target.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")
            created = True
        try:
            data = client.get("/api/pose-photos").get_json()
            assert data["photos"].get("3") == f"/static/images/poses/{target.name}"
        finally:
            if created:
                target.unlink()

    def test_covers_all_24_poses_in_contract(self):
        assert set(POSE_PHOTO_BASENAMES.keys()) == set(range(1, 25))
