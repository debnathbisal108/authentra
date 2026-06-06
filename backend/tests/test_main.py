import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import Base, get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.services.resume_parser import extract_text_from_docx
from app.services.fraud_detection import analyze_fraud
import uuid

# ─── Test DB setup ────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─── Security tests ──────────────────────────────────────────────────────────

def test_password_hashing():
    password = "testpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_jwt_create_decode():
    data = {"sub": str(uuid.uuid4()), "org": str(uuid.uuid4()), "role": "recruiter"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == data["sub"]
    assert decoded["type"] == "access"


def test_jwt_invalid():
    result = decode_token("invalid.token.here")
    assert result is None


# ─── API Health ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ─── Auth tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/api/v1/auth/register", json={
        "company_name": "Test Corp",
        "admin_email": "admin@testcorp.com",
        "password": "securepass123",
        "first_admin_name": "Test Admin",
    })
    assert response.status_code == 201
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "company_name": "Dupe Corp",
        "admin_email": "dupe@testcorp.com",
        "password": "securepass123",
        "first_admin_name": "Dupe Admin",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_invalid(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_and_login(client):
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    await client.post("/api/v1/auth/register", json={
        "company_name": "Login Test Corp",
        "admin_email": email,
        "password": "testpass123",
        "first_admin_name": "Login User",
    })
    # Manually verify email in DB for login to work
    async with TestSessionLocal() as db:
        from sqlalchemy import select, update
        from app.models.models import User
        await db.execute(update(User).where(User.email == email).values(email_verified=True))
        await db.commit()

    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ─── Fraud detection tests ────────────────────────────────────────────────────

def test_fraud_no_flags():
    employment = [
        {"company_name": "TechCorp", "job_title": "Engineer", "start_date": "Jan 2020", "end_date": "Dec 2021", "is_current": False},
        {"company_name": "StartupXYZ", "job_title": "Senior Engineer", "start_date": "Jan 2022", "end_date": None, "is_current": True},
    ]
    education = [
        {"institution_name": "MIT", "degree": "BS", "start_year": "2016", "end_year": "2020"},
    ]
    flags = analyze_fraud(employment, education, "Python Java AWS")
    assert isinstance(flags, list)


def test_fraud_detects_overlapping_jobs():
    employment = [
        {"company_name": "Company A", "job_title": "Engineer", "start_date": "Jan 2020", "end_date": "Dec 2021", "is_current": False},
        {"company_name": "Company B", "job_title": "Engineer", "start_date": "Jun 2020", "end_date": "Jun 2022", "is_current": False},
    ]
    flags = analyze_fraud(employment, [], "")
    flag_types = [f["flag_type"] for f in flags]
    assert "OVERLAPPING_EMPLOYMENT" in flag_types


def test_fraud_detects_impossible_dates():
    employment = [
        {"company_name": "BadCorp", "job_title": "Manager", "start_date": "Dec 2022", "end_date": "Jan 2020", "is_current": False},
    ]
    flags = analyze_fraud(employment, [], "")
    flag_types = [f["flag_type"] for f in flags]
    assert "IMPOSSIBLE_DATES" in flag_types


def test_fraud_keyword_stuffing():
    text = " ".join(["python java kubernetes docker aws react angular"] * 50)
    flags = analyze_fraud([], [], text)
    flag_types = [f["flag_type"] for f in flags]
    assert "KEYWORD_STUFFING" in flag_types


# ─── Encryption tests ─────────────────────────────────────────────────────────

def test_encrypt_decrypt():
    from app.core.security import encrypt_field, decrypt_field
    original = "test@example.com"
    encrypted = encrypt_field(original)
    assert encrypted != original
    decrypted = decrypt_field(encrypted)
    assert decrypted == original


def test_encrypt_empty():
    from app.core.security import encrypt_field
    result = encrypt_field("")
    assert result == ""


# ─── Candidates endpoint (auth required) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_candidates_requires_auth(client):
    response = await client.get("/api/v1/candidates/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code in (401, 403)


# ─── Consent token tests ──────────────────────────────────────────────────────

def test_consent_token_valid():
    from app.core.security import create_consent_token, verify_consent_token
    candidate_id = str(uuid.uuid4())
    token = create_consent_token(candidate_id)
    result = verify_consent_token(token)
    assert result == candidate_id


def test_consent_token_invalid():
    from app.core.security import verify_consent_token
    result = verify_consent_token("invalid_token")
    assert result is None
