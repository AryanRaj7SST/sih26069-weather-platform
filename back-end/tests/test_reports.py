import io

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.db.session import async_session_factory
from app.main import app
from app.models.media import ReportMedia
from app.models.report import WeatherReport
from app.services.storage import storage_service


@pytest.fixture(autouse=True)
def ensure_storage_ready():
    """Ensure MinIO bucket exists before running tests."""
    storage_service.ensure_bucket_exists()


@pytest.mark.asyncio
async def test_submit_citizen_report_success():
    """Test successful submission of a citizen report without media attachments."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "19.0760",
            "longitude": "72.8777",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "HIGH",
            "title": "Severe knee-deep waterlogging near station subway",
            "description": "Traffic completely halted. Water level rising steadily.",
            "location_name": "Kurla Station West, Mumbai",
        }

        response = await client.post("/api/v1/reports", data=form_data)

        assert response.status_code == 201, response.text
        json_data = response.json()

        assert json_data["success"] is True
        assert "data" in json_data
        data = json_data["data"]

        assert "id" in data
        assert data["tracking_id"].startswith("RPT-")
        assert data["processing_status"] == "QUEUED"
        assert data["verification_status"] == "PENDING"
        assert data["media_count"] == 0
        assert "meta" in json_data
        assert "request_id" in json_data["meta"]

        # Verify DB persistence directly
        async with async_session_factory() as session:
            stmt = select(WeatherReport).where(WeatherReport.id == data["id"])
            result = await session.execute(stmt)
            db_report = result.scalar_one_or_none()

            assert db_report is not None
            assert db_report.title == form_data["title"]
            assert db_report.severity == "HIGH"
            assert db_report.latitude == 19.0760
            assert db_report.longitude == 72.8777
            assert db_report.processing_status == "QUEUED"
            assert db_report.verification_status == "PENDING"
            assert db_report.credibility_score == 0.0

            # Verify spatial point representation in PostGIS
            spatial_query = await session.execute(
                text(
                    "SELECT ST_AsText(geom) AS point_text "
                    "FROM weather_reports WHERE id = :report_id"
                ),
                {"report_id": data["id"]},
            )
            row = spatial_query.fetchone()
            assert row is not None
            assert row[0] == "POINT(72.8777 19.076)"


@pytest.mark.asyncio
async def test_submit_citizen_report_with_media():
    """Test successful submission of a citizen report with an attached image."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "18.5204",
            "longitude": "73.8567",
            "category_code": "HEAVY_RAINFALL",
            "severity": "MODERATE",
            "title": "Continuous heavy downpour in Shivajinagar",
            "description": "Drainage overflowing along the main arterial road.",
            "location_name": "Shivajinagar, Pune",
        }

        fake_png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png_binary_data"
        fake_image = io.BytesIO(fake_png_data)
        files = [
            ("media_files", ("flood_photo.png", fake_image, "image/png")),
        ]

        response = await client.post(
            "/api/v1/reports",
            data=form_data,
            files=files,
        )

        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["media_count"] == 1

        # Verify media metadata in database and file in MinIO
        async with async_session_factory() as session:
            stmt = select(ReportMedia).where(ReportMedia.report_id == data["id"])
            result = await session.execute(stmt)
            media_record = result.scalar_one_or_none()

            assert media_record is not None
            assert media_record.media_type == "IMAGE"
            assert media_record.mime_type == "image/png"
            assert media_record.file_size_bytes == len(fake_png_data)
            assert len(media_record.sha256_hash) == 64

            # Verify MinIO S3 object exists
            s3_obj = storage_service.client.get_object(
                Bucket=media_record.storage_bucket,
                Key=media_record.storage_key,
            )
            downloaded_bytes = s3_obj["Body"].read()
            assert downloaded_bytes == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png_binary_data"


@pytest.mark.asyncio
async def test_submit_report_invalid_latitude():
    """Test validation rejection when latitude exceeds 90 degrees."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "95.5000",
            "longitude": "72.8777",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "MODERATE",
            "title": "Invalid latitude report",
        }
        response = await client.post("/api/v1/reports", data=form_data)
        assert response.status_code == 422
        json_data = response.json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_submit_report_invalid_longitude():
    """Test validation rejection when longitude exceeds 180 degrees."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "19.0760",
            "longitude": "-195.0000",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "MODERATE",
            "title": "Invalid longitude report",
        }
        response = await client.post("/api/v1/reports", data=form_data)
        assert response.status_code == 422
        json_data = response.json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_submit_report_missing_title():
    """Test validation rejection when required title field is omitted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "19.0760",
            "longitude": "72.8777",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "MODERATE",
        }
        response = await client.post("/api/v1/reports", data=form_data)
        assert response.status_code == 422
        json_data = response.json()
        assert json_data["success"] is False


@pytest.mark.asyncio
async def test_submit_report_unsupported_media_mime_type():
    """Test rejection when uploading an unsupported file type."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "19.0760",
            "longitude": "72.8777",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "MODERATE",
            "title": "Report with unsupported PDF",
        }
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake_pdf_content")
        files = [
            ("media_files", ("document.pdf", fake_pdf, "application/pdf")),
        ]
        response = await client.post("/api/v1/reports", data=form_data, files=files)
        assert response.status_code == 400
        json_data = response.json()
        assert json_data["success"] is False
        assert "Unsupported media MIME type" in json_data["error"]["message"]


@pytest.mark.asyncio
async def test_tracking_id_uniqueness():
    """Test that consecutive reports receive distinct tracking identifiers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        form_data = {
            "latitude": "19.0760",
            "longitude": "72.8777",
            "category_code": "FLOOD_WATERLOGGING",
            "severity": "LOW",
            "title": "Report 1 for tracking test",
        }
        res1 = await client.post("/api/v1/reports", data=form_data)
        res2 = await client.post("/api/v1/reports", data=form_data)

        assert res1.status_code == 201
        assert res2.status_code == 201

        id1 = res1.json()["data"]["tracking_id"]
        id2 = res2.json()["data"]["tracking_id"]
        assert id1 != id2
