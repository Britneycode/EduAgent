from __future__ import annotations

from app.core.storage import LocalAssetStorage


def test_local_asset_storage_saves_and_resolves_file(tmp_path) -> None:
    storage = LocalAssetStorage(tmp_path, public_url_prefix="/api/assets")

    asset = storage.save_bytes(
        data=b"hello",
        filename="report.md",
        media_type="text/markdown",
        namespace="resource-1",
    )

    assert asset.url.startswith("/api/assets/resource-1/")
    assert asset.size_bytes == 5
    assert asset.path.read_bytes() == b"hello"
    assert storage.resolve(asset.key) == asset.path
    assert storage.resolve("../secret.txt") is None
