# MusicAsLanguage web service

Flask/MongoEngine API for lessons, progress, accounts, messages, and speech scoring.
Python 3.12 is the supported development, deployment, and CI runtime. NumPy 2.5.3
requires Python 3.12 or newer; recreate existing Python 3.11 virtual environments
with Python 3.12 before installing the updated dependencies.

## Development and tests

Create a virtual environment and install the development dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest --cov --cov-report=term-missing
ruff check .
```

On Linux, create the environment with `python3.12 -m venv .venv` and activate it
with `source .venv/bin/activate`; the pip, pytest, and Ruff commands are the same.
Windows CMD users can use `setup_venv.bat` and `test.bat`.

Tests use mongomock by default. They do not download a speech model, contact an
email provider, or use `MONGODB_SETTINGS`. Each test owns a randomly named
`mal_test_<uuid>` database, drops only that database, and disconnects afterward.
The cleanup guard refuses to drop a database it does not own.

To run the same suite against a dedicated MongoDB 7 instance:

```powershell
$env:TEST_MONGODB_URI = "mongodb://127.0.0.1:27017"
python -m pytest --cov --cov-report=term-missing
Remove-Item Env:TEST_MONGODB_URI
```

The test URI must not contain a database name. Use a dedicated test server and
credentials allowed to create/drop disposable databases, not a production server.
Concurrency and unique-index checks run with both backends.

## Local server

Install MongoDB separately, then configure its URI:

```powershell
$env:APP_ENV = "dev"
$env:MONGODB_SETTINGS = "mongodb://localhost:27017/MusicAsLanguage"
python app.py
```

The development server listens on port 8000. The app factory is
`app:create_app`; importing `app` alone does not connect to MongoDB or load
Whisper. Test callers can pass configuration overrides, including `MAIL_SENDER`
and `TRANSCRIBER` callables, to `create_app("test", overrides)`.

Speech processing additionally requires FFmpeg on `PATH` and:

```powershell
python -m pip install -r requirements-speech.txt
```

The model loads lazily on the first valid speech request, once per process.
Provision/cache Whisper's `tiny` model before serving traffic if outbound model
downloads are unavailable. Only one transcription runs per process; concurrent
speech requests receive 503 rather than accumulating in an unbounded queue.
Uploads are limited to 10 MiB, audio to 120 seconds, and text to 2,000 characters.
Temporary audio is removed on success and failure; raw transcripts are not logged.

The development Docker helpers forward `MONGODB_SETTINGS` and `SEND_GRID_KEY`
from the caller instead of embedding database credentials. For Docker Desktop,
use `host.docker.internal` instead of `localhost` in the database URI.

## API compatibility and behavior

Existing API routes, field casing, and success response shapes are retained:

| Request | Example body / behavior |
|---|---|
| `POST /api/auth/signup` | `{"name":"Jane","email":"jane@example.com","password":"my-password"}` |
| `POST /api/auth/login` | `{"email":"jane@example.com","password":"my-password"}`; returns `token` and `refresh_token` |
| `POST /api/auth/tokenRefresh` | Refresh token in the Bearer authorization header |
| `GET /api/lesson/getLessons` | Public lesson metadata |
| `POST /api/lesson/createLessons` | Administrator-only array of programs |
| `GET /health/ready` | 200 only when MongoDB responds |

Invalid/missing JSON fields now return 4xx instead of 500. Unknown or server-owned
fields are rejected. Completion status is an integer from 0 to 10; repeats and
scores must be nonnegative integers. Signup and reset validate passwords before
hashing: 6 to 100 characters, with a 72-byte UTF-8 maximum imposed by bcrypt.

New access tokens expire after one hour and refresh tokens after 30 days.
Clients must refresh expired access tokens. Existing serialized-user identities
remain supported. Existing non-expiring tokens are not retroactively expired:
rotate the signing key to invalidate them globally, or reset a user's password
to invalidate that user's sessions. Signing-key rotation forces users to log in.

Password-reset tokens have a separate purpose, expire after 24 hours, are
single-use, and cannot authorize API access. Password reset invalidates both
access and refresh tokens for the user. Old reset links must be requested again.
Failure to send a confirmation email is logged but does not undo a completed
password change. Likewise, a saved message remains successful if its notification
email fails; the delivery failure is logged.

Progress records are unique by `(User, ActivityId, LessonId)` or `(User, SongName)`.
Song names remain the legacy identifier; changing category updates the existing
song record. Updates are atomic; unchanged progress preserves its timestamp.
Speech awards increment the score atomically, while `updateUserScore` deliberately
retains its existing score-replacement semantics.

Lesson batches are completely validated before writing. Each program is updated
atomically without deleting its predecessor. A database failure midway through a
batch can still leave earlier programs updated: the API returns an error, clears
the local cache, and the administrator can retry the batch. There is no claim of
cross-program transactional rollback. Metadata has a 60-second TTL; publication
invalidates the current worker immediately, and other workers expire within that
TTL. `/clearCache` requires an exact administrator email match.

Account deletion removes activity progress, song progress, and stored messages
before deleting the user. It does not remove copies already delivered to an
external email provider or mailbox.

## CI and deployment gates

Both PR-to-test and main-to-PPE workflows call the reusable
`.github/workflows/checks.yml` workflow **before** building, pushing, or deploying.
It requires Ruff, the complete pytest suite against both mongomock and MongoDB 7,
at least **90% combined statement/branch coverage**, and a production container
build with dependency consistency, runtime import/tool, and Whisper audio-processing
smoke checks. The container check installs the real speech dependencies and converts
a NumPy audio array into a finite, correctly shaped Whisper mel spectrogram without
downloading model weights, catching packaging and NumPy/PyTorch compatibility
failures that injected transcription tests cannot detect. A failed, cancelled, or
skipped check cannot satisfy the final `Quality gate` job. Tests do not need
deployment secrets; fork and Dependabot PRs run checks but skip deployment.

To also block merging failing PRs, configure the repository's `main` branch
ruleset/protection to require the `Checks / Quality gate` status check after its
first run. Workflow dependencies gate deployment; they do not themselves change
GitHub branch-protection settings.

The container uses the official `python:3.12-slim` image from Docker Hub; the
previous Microsoft mirror does not provide the Python 3.12 slim tag.
It uses Gunicorn rather than Flask's development server, with one
worker and four threads by default. `WEB_CONCURRENCY` controls worker count;
each worker loads its own speech model, so size this against available memory.
The readiness endpoint checks MongoDB, not email-provider or model availability.

Before deploying this version:

1. Back up existing data and reconcile duplicate progress keys. Run
   `flask --app app:create_app prepare-indexes` with the intended environment
   configuration. It refuses duplicates without deleting data and creates the
   compound unique indexes when safe. Do not roll out competing old writers
   during this operation.
2. Set `APP_ENV=prod`, `MONGODB_SETTINGS` (MongoDB URI), independent random
   `SECRET_KEY` and `JWT_SECRET_KEY` values of at least 32 characters,
   `PUBLIC_BASE_URL` (the public HTTPS origin), and `ADMIN_USERS` (comma-separated
   exact email addresses). Production fails startup when required settings are
   absent. Keep an existing valid JWT signing key if retaining current sessions
   is required.
3. Set `SEND_GRID_KEY` for email delivery. Missing configuration fails explicitly;
   development/tests do not silently report successful delivery.
4. Confirm mobile clients handle refresh, the new validation responses, and the
   documented password limits before promoting to production.
