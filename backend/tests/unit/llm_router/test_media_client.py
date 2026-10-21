import base64
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.llm_router.infra import media_client as media_module
from src.llm_router.infra.media_client import MediaClient, SrvMediaConfig
from src.shared.domain.exceptions import BadRequestError
from src.shared.infra.services.exceptions import SrvBaseError


def _response(status, data):
    response = AsyncMock()
    response.status = status
    response.json.return_value = data
    context = AsyncMock()
    context.__aenter__.return_value = response
    return context


@pytest.fixture
def upload_flow(monkeypatch):
    upload_id = uuid4()
    api = MagicMock()
    presigned = {"id": str(upload_id), "upload": {
        "url": "https://storage.test/upload", "expiresIn": 60,
        "headers": {"x-upload-header": "signed-value"},
    }}
    api.post.side_effect = [_response(200, presigned), _response(201, {"storage_key": "output.png"})]
    storage = MagicMock()
    storage.put.return_value = _response(200, {})
    storage_context = AsyncMock()
    storage_context.__aenter__.return_value = storage
    monkeypatch.setattr(media_module, "ClientSession", MagicMock(return_value=storage_context))
    api_context = AsyncMock()
    api_context.__aenter__.return_value = api
    client = MediaClient(SrvMediaConfig(
        base_url="http://media.test", client_id="test", client_secret="test",
    ))
    client._get_token_session = MagicMock(return_value=api_context)
    return client, api, storage, upload_id, presigned


@pytest.mark.asyncio
@pytest.mark.parametrize(("content", "extension"), [
    (b"\x89PNG\r\n\x1a\nbytes", "png"), (b"\xff\xd8\xffbytes", "jpeg"),
    (b"GIF89abytes", "gif"), (b"RIFF\x00\x00\x00\x00WEBPbytes", "webp"),
])
async def test_save_image_uses_existing_api_and_original_bytes(upload_flow, content, extension):
    client, api, storage, upload_id, _ = upload_flow

    key = await client.save_image(base64.b64encode(content).decode(), "llm-inputs")

    assert key == "output.png"
    assert api.post.call_count == 2
    api.post.assert_any_call("/api/v1/attachments/presigned-upload", json={
        "filename": f"image.{extension}", "contentType": f"image/{extension}",
        "folder": "llm-inputs", "sizeBytes": len(content), "sha256": sha256(content).hexdigest(),
    })
    api.post.assert_any_call(f"/api/v1/attachments/confirm-upload/{upload_id}")
    storage.put.assert_called_once_with("https://storage.test/upload", data=content, headers={
        "Content-Type": f"image/{extension}", "x-upload-header": "signed-value",
    })
    assert "Authorization" not in storage.put.call_args.kwargs["headers"]


@pytest.mark.asyncio
@pytest.mark.parametrize("image", ["!bad!", "", base64.b64encode(b"not an image").decode()])
async def test_invalid_image_makes_no_http_calls(upload_flow, image):
    client, api, storage, _, _ = upload_flow
    with pytest.raises(BadRequestError):
        await client.save_image(image, "llm-inputs")
    api.post.assert_not_called()
    storage.put.assert_not_called()


@pytest.mark.asyncio
async def test_presigned_error_stops_upload(upload_flow):
    client, api, storage, _, _ = upload_flow
    api.post.side_effect = [_response(500, {})]
    with pytest.raises(SrvBaseError, match="presigned upload failed"):
        await client.save_image(base64.b64encode(b"\xff\xd8\xffbytes").decode(), "llm-inputs")
    storage.put.assert_not_called()


@pytest.mark.asyncio
async def test_s3_error_stops_confirmation(upload_flow):
    client, api, storage, _, _ = upload_flow
    storage.put.return_value = _response(503, {})
    with pytest.raises(SrvBaseError, match="S3 image upload failed"):
        await client.save_image(base64.b64encode(b"\xff\xd8\xffbytes").decode(), "llm-inputs")
    api.post.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "data"), [(400, {}), (201, {}), (201, {"storage_key": ""})])
async def test_confirm_error_does_not_return_fake_key(upload_flow, status, data):
    client, api, _, _, presigned = upload_flow
    api.post.side_effect = [_response(200, presigned), _response(status, data)]
    with pytest.raises(SrvBaseError):
        await client.save_image(base64.b64encode(b"\xff\xd8\xffbytes").decode(), "llm-inputs")
