import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.ml_client import get_prediction
from app.services.training_client import train_model
from app.services.batch_prediction_client import predict_batch


@pytest.mark.asyncio
async def test_get_prediction_success():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"probability": 0.5}
        mock_post.return_value = mock_response

        result = await get_prediction({"age": 25})
        assert result["probability"] == 0.5


@pytest.mark.asyncio
async def test_get_prediction_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        # Правильно настраиваем исключение
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=httpx.Request("POST", "http://test"), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError):
            await get_prediction({"age": 25})


@pytest.mark.asyncio
async def test_train_model_success():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"model_id": "123"}
        mock_post.return_value = mock_response

        result = await train_model("file.csv", b"data", "target")
        assert result["model_id"] == "123"


@pytest.mark.asyncio
async def test_predict_batch_success():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_records": 1, "results": []}
        mock_post.return_value = mock_response

        result = await predict_batch([{"age": 25}])
        assert result["total_records"] == 1


@pytest.mark.asyncio
async def test_train_model_validation_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "Bad data"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=httpx.Request("POST", "url"), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValueError):
            await train_model("file.csv", b"data", "target")


@pytest.mark.asyncio
async def test_predict_batch_validation_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "Bad data"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=httpx.Request("POST", "url"), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValueError):
            await predict_batch([{"age": 25}])


@pytest.mark.asyncio
async def test_predict_batch_no_model_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=httpx.Request("POST", "url"), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError):
            await predict_batch([{"age": 25}])