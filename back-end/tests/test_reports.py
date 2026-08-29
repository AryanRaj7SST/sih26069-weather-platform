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
            assert downloaded_bytes == fake_png_data


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


@pytest.mark.asyncio
async def test_get_report_by_tracking_id_success():
    """Test retrieving public status of a report using its tracking ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a report
        create_res = await client.post(
            "/api/v1/reports",
            data={
                "latitude": "28.6139",
                "longitude": "77.2090",
                "category_code": "EXTREME_HEAT",
                "severity": "HIGH",
                "title": "Heatwave alert in Central Delhi",
                "description": "Temperature crossed 45 degrees Celsius.",
                "location_name": "Connaught Place, New Delhi",
            },
        )
        assert create_res.status_code == 201
        tracking_id = create_res.json()["data"]["tracking_id"]
        report_id = create_res.json()["data"]["id"]

        # Look up by tracking ID
        get_res = await client.get(f"/api/v1/reports/{tracking_id}")
        assert get_res.status_code == 200
        json_data = get_res.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert data["id"] == report_id
        assert data["tracking_id"] == tracking_id
        assert data["title"] == "Heatwave alert in Central Delhi"
        assert data["severity"] == "HIGH"
        assert data["processing_status"] == "QUEUED"
        assert data["verification_status"] == "PENDING"
        assert data["credibility_score"] == 0.0
        assert data["location"]["latitude"] == 28.6139
        assert data["location"]["longitude"] == 77.2090
        assert data["location"]["name"] == "Connaught Place, New Delhi"
        assert data["category"]["code"] == "EXTREME_HEAT"


@pytest.mark.asyncio
async def test_get_report_by_uuid_success():
    """Test retrieving report using its UUID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/reports",
            data={
                "latitude": "12.9716",
                "longitude": "77.5946",
                "category_code": "URBAN_FLOOD",
                "severity": "MODERATE",
                "title": "Waterlogging in Koramangala",
                "location_name": "Koramangala 4th Block, Bengaluru",
            },
        )
        assert create_res.status_code == 201
        report_id = create_res.json()["data"]["id"]
        tracking_id = create_res.json()["data"]["tracking_id"]

        get_res = await client.get(f"/api/v1/reports/{report_id}")
        assert get_res.status_code == 200
        data = get_res.json()["data"]
        assert data["id"] == report_id
        assert data["tracking_id"] == tracking_id


@pytest.mark.asyncio
async def test_get_report_nonexistent_returns_404():
    """Test that looking up a nonexistent tracking ID returns 404 with standard error envelope."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/reports/RPT-20260101-NONEXISTENT")
        assert response.status_code == 404
        json_data = response.json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "does not exist" in json_data["error"]["message"]


@pytest.mark.asyncio
async def test_get_report_malformed_id_returns_422():
    """Test that malformed identifier (spaces, invalid symbols) returns 422 validation error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/reports/bad%20id%20with%20spaces!")
        assert response.status_code == 422
        json_data = response.json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_report_privacy_no_internal_leak():
    """Test that public tracking response excludes internal DB keys, audit logs, and secrets."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/reports",
            data={
                "latitude": "19.0760",
                "longitude": "72.8777",
                "category_code": "CYCLONE_STORM",
                "severity": "SEVERE",
                "title": "Severe coastal wind gusts",
            },
        )
        tracking_id = create_res.json()["data"]["tracking_id"]

        get_res = await client.get(f"/api/v1/reports/{tracking_id}")
        data = get_res.json()["data"]

        # Ensure private/internal fields are NOT present in public response
        assert "source_id" not in data
        assert "raw_payload" not in data
        assert "text_embedding" not in data
        assert "credibility_explanation" not in data
        assert "audit_logs" not in data
