# MusicAsLanguage web service

Flask/MongoEngine API for lessons, progress, accounts, messages, and speech scoring.
Standard (GIL-enabled) CPython 3.14 is the supported development, deployment, and
CI runtime; free-threaded builds are not supported. Recreate virtual environments
built with an older interpreter using Python 3.14 before installing dependencies.
The development requirements use pytest 8.4.2 and Ruff 0.14.14 for supported
Python 3.14 testing and linting. Runtime dependency pins, including NumPy 2.5.3
and Whisper 20250625, are unchanged.

The service uses Flask 3.1.3, Werkzeug 3.1.9, and MongoEngine 0.29.3 directly.
The obsolete `flask-mongoengine` wrapper was removed in
[the direct MongoEngine migration](https://github.com/MusicAsLanguage/webservice/commit/5ffdd2061595a0c098cf0b63b3d2636f869581a5)
and is not required. `database.db.initialize_db` passes a MongoDB URI or a copied
settings dictionary to `mongoengine.connect`, preserving explicit options and
defaulting `serverSelectionTimeoutMS` to 5,000 ms. Connections remain available
across requests; the test fixtures explicitly disconnect after database cleanup.
Flask's default JSON provider and the existing API serialization are unchanged.

## Development and tests

Create a virtual environment and install the development dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest --cov --cov-report=term-missing
ruff check .
```

On Linux, create the environment with `python3.14 -m venv .venv` and activate it
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
downloads are unavailable. Only one speech request parses/saves audio, decodes, and transcribes per process;
concurrent speech requests receive 503 before multipart parsing rather than
accumulating files or waiting in an unbounded queue. The lazy model also retains
its own inference lock.
Upload requests, including their multipart envelope, are limited to 10 MiB,
audio to 120 seconds, and text to 2,000 characters.
Temporary audio is removed on success and failure; raw transcripts are not logged.
`MAX_SPEECH_UPLOAD_BYTES` applies only to speech, not lesson publication or other
JSON APIs. An explicitly configured Flask `MAX_CONTENT_LENGTH` can impose a
smaller deployment-wide limit; no deployment-wide limit is set by this service.

The [Flask 3.1 multipart parser defaults](https://flask.palletsprojects.com/en/stable/config/#MAX_FORM_MEMORY_SIZE)
are retained: each non-file field is limited to 500,000 bytes and a request to
1,000 parts (`MAX_FORM_MEMORY_SIZE` and `MAX_FORM_PARTS`). Exceeding either parser
limit or the total request limit returns the existing JSON error shape with HTTP
413 before transcription or scoring. Audio files larger than 500,000 bytes remain
accepted within the total request limit; the field limit is not a file-size limit.
The application's 2,000-character speech-text validation still returns HTTP 400
for text that passes parsing but exceeds that application limit.

The development Docker helpers forward `MONGODB_SETTINGS` and `SEND_GRID_KEY`
from the caller instead of embedding database credentials. For Docker Desktop,
use `host.docker.internal` instead of `localhost` in the database URI.

## API compatibility and behavior

Compatibility means the following legacy methods, field casing, valid payload
encodings, success status/envelopes, and MongoEngine extended-JSON shapes remain
supported. It does **not** mean restoring insecure behavior or accepting every
input that accidentally succeeded before validation existed. The frozen
[`tests/fixtures/legacy_contracts.json`](tests/fixtures/legacy_contracts.json)
records the pre-refactor `70e0251` source/blob IDs and independently reproduced
model/error output. It is not regenerated from the current API. The contract
suite exercises all 16 REST resources and all three original web routes;
readiness is tested separately.

| Request | Example body / behavior |
|---|---|
| `POST /api/auth/signup` | `{"name":"Jane","email":"jane@example.com","password":"my-password"}` |
| `POST /api/auth/login` | `{"email":"jane@example.com","password":"my-password"}`; returns `token` and `refresh_token` |
| `POST /api/auth/tokenRefresh` | Refresh token in the Bearer authorization header |
| `GET /api/lesson/getLessons` | Public lesson metadata |
| `POST /api/lesson/createLessons` | Administrator-only array of programs |
| `POST /api/auth/forgotPwd` | `{"email":"jane@example.com"}`; `{"status":"Password reset email has been sent to jane@example.com"}` |
| `POST /api/auth/resetPwd` | `{"reset_token":"...","password":"new-password"}`; `{"status":"Password reset was successful!"}` |
| `GET /api/activity/getStatus` | Array of the caller's activity records |
| `POST /api/activity/updateStatus` | `{"ActivityId":"1","LessonId":"2","CompletionStatus":"5"}`; `{"id":"<object-id>"}` |
| `GET /api/activity/getSongPlayingStatus` | Array of the caller's song records |
| `POST /api/activity/updateSongPlayingStatus` | `{"SongName":"Song","Category":"Beginner","CompletionStatus":5}`; `{"id":"<object-id>"}` |
| `GET /api/user/getUserScore` | `{"score":0}` |
| `POST /api/user/updateUserScore` | `{"score":"100"}` replaces the caller's score; `{"success":true}` |
| `DELETE /api/user/deleteUserAndData` | `{"success":true}` after stored account data is deleted |
| `POST /api/msg/send` | `{"Msg":"Hello"}`; `{"id":"<object-id>"}` |
| `POST /api/user/speechScore` | Multipart `speech_text` and `music_file`; `{"text":"recognized text","score":10}` |
| `GET /clearCache` | Exact administrator membership required; literal `Cache cleared!`, legacy JSON content type |
| `GET /resetPwd/<token>` | HTML form containing the supplied token |
| `POST /resetPwd` | Form `reset_token` and `password`; HTML with success **only** after a successful reset |
| `GET /health/ready` | 200 only when MongoDB responds |

Successful requests above return 200. Signup returns `{"id":"<object-id>"}`;
login returns `token` and `refresh_token`, refresh returns `token`; publication
returns the legacy stringified numeric array, e.g. `{"id":"[1, 2]"}`.
Lists remain arrays, IDs use `{"$oid":"..."}`, references use
`{"$ref":"user","$id":{"$oid":"..."}}`, and dates use integer epoch milliseconds
in `{"$date":...}`. Program IDs are numeric, not generated ObjectIds.
Omitted optional lesson fields are absent, not newly introduced `null` values;
list defaults remain `[]` and activity `PracticeMode` defaults to `false`.

Progress IDs, repeats and scores accept nonnegative signed-64-bit integers,
ASCII decimal strings (including surrounding whitespace, sign and leading zeros),
and exactly integral JSON numbers within the safe floating-point integer range
0 through 9,007,199,254,740,991. Completion status is limited to 0 through 10.
Booleans, fractional values, exponent/decimal strings, negative values and
overflow are rejected instead of being truncated or silently coerced.
`Repeats` still defaults to zero when omitted or explicitly `null`. Category is
required for a new song record; omitting it or sending `null` on an existing
record preserves its value. An explicit non-null category
change remains supported as introduced in #62; unlike the original implementation,
it is no longer silently ignored.

Known harmless metadata is accepted but **never trusted or persisted**:
signup ignores `id`, `_id`, `UpdateTime`; login additionally ignores `name` and
`score`; forgot/reset ignore those same user metadata fields (forgot also ignores
an unused `password`, while reset requires `password` and ignores `email`).
Progress ignores `id`, `_id`, `User`, `UpdateTime`; score ignores those fields
plus `name`/`email`/`password`; messages ignore `id`, `_id`, `User`.
Original model constructors accepted `id`, not `_id`; tolerating `_id` is an
additional safe serialization-round-trip convenience. Authentication state,
deletion fields, privileges and truly unknown fields are rejected. Initial signup
score is server-owned. Caller-supplied IDs cannot select/overwrite another account
or record, and caller timestamps never replace server progress timestamps.

Signup/reset support **6 to 100 characters**, including Unicode and whitespace;
there is no 72-byte rejection. New passwords use a self-versioned
`$bcrypt-sha256$` hash: bcrypt of the hexadecimal SHA-256 of the entire UTF-8
password. Different long suffixes are compared correctly; passwords are never
stored in plaintext or normalized. Existing bcrypt hashes retain their historical
72-byte truncation semantics, including a Unicode character cut at that boundary.
Those old hashes inherently cannot distinguish suffixes after byte 72; a password
reset migrates to full-password comparison. Login also verifies historical short
passwords (1 to 100 characters), but new passwords must meet the 6-character
minimum. Hash/version/lifecycle internals do not appear in access-token user JSON.

This is **client API compatibility**, not backward readability by old server
binaries. Once new `$bcrypt-sha256$` hashes are written, older builds without this
verifier cannot authenticate those accounts. Do not mix old/new authentication
workers. Any rollback must retain the new hash reader; hashes cannot be converted
back to legacy bcrypt without the users' passwords. Deploy compatible readers
everywhere before allowing new-format writes: pause traffic, stop old workers,
replace all instances, then resume traffic. There is no mixed-version writer
switch in this release.

New access tokens expire after one hour and refresh tokens after 30 days.
Clients must refresh expired access tokens. Existing serialized-user identities
remain supported. Existing non-expiring tokens are not retroactively expired:
rotate the signing key to invalidate them globally, or reset a user's password
to invalidate that user's sessions. Signing-key rotation forces users to log in.

Password-reset tokens have a separate purpose, expire after 24 hours, are
single-use, and cannot authorize API access. Password reset invalidates both
access and refresh tokens for the user. A narrowly identified old reset link is
still accepted: signed access token, plain ObjectId subject, `fresh=false`, no
purpose/version claims, and an **exact 24-hour** issued-at-to-expiry lifetime,
not expired, for an existing non-deleting user still at auth version zero.
The old issuer's links therefore age out within 24 hours after that issuer is
retired; this is not a new indefinite token format. Other purpose-less plain-ID
access tokens are rejected, not treated as sessions. Old serialized-user access
tokens (including no-expiry tokens) and plain-ID refresh tokens remain session-only.
Session/refresh tokens cannot reset passwords; reset links cannot use any
authenticated API. Missing, partial, null or ill-typed purpose/version claims
cannot bypass these distinctions. Reused/revoked/expired/deleted-user reset links
must be requested again.
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
before deleting the user. It first atomically marks the user as deleting, blocking
new authenticated work except deletion retries. Short owned-data writes acquire
an atomic admission count on the user; deletion returns **409** while these drain
and can be retried with the same access token. A normal write error releases its
admission. No admission is held while transcribing or contacting email providers.
Cleanup failure leaves the deleting user in place and returns an explicit error;
retry resumes safely, including concurrent already-authenticated delete requests.
Once removed, all tokens return 401 (reset links return 403), not a fake successful
authenticated retry. A fresh login can obtain a deletion-only session when a
partially deleted account's access token has expired.

This is not a multi-document transaction or a crash-proof distributed lock.
A worker crash or uncertain database acknowledgement can leave a nonzero
admission count. **Never expire/reset it automatically:** a still-running writer
could otherwise recreate records after deletion. Recovery requires stopping
**all** API workers and any other database writers, confirming there are no
in-flight writes, then running the account-scoped command with the intended
environment configuration:

```powershell
flask --app app:create_app recover-deletion --user-id <object-id> --writers-stopped
```

It refuses absent/non-deleting accounts, invalid IDs and missing confirmation;
it resets only that deleting account's count and finishes its owned-data cleanup.
Back up data first; retry under the same outage if cleanup fails, and restart
workers only afterward. The flag is an operator assertion, not automatic proof
that other processes are stopped. Never use manual broad counter resets.
Email already sent or in flight is not recalled; external mailbox/provider copies
are outside stored-account deletion.

### Intentional security and error-contract exceptions

Malformed/missing JSON now returns 400 (wrong media type 415), not an accidental
500. Established domain errors retain `{"message":"...","status":400}` (or
401/403/409/500/503 as applicable), restoring the original Flask-RESTful mapping's
numeric `status` field without removing #62's `message`. JWT failures deliberately
return 401 `{"message":"Invalid or missing token"}` rather than the old RESTful
500. HTTP/parser errors use `{"message":"..."}` and their HTTP status; reset form
errors are rendered in HTML. Unexpected service failures are logged, not exposed
to callers. Clients should use HTTP status and allow additive error fields.

Administrator substring matches, unauthenticated cache clearing, caller-controlled
ownership/IDs/auth state, plaintext password writes and reset-token API access
remain prohibited. Speech requires nonblank text, at most 2,000 characters,
10 MiB multipart requests and 120 seconds of audio; malformed/empty audio is a
client error, overload returns 503, and total score overflow is rejected.
Messages require nonblank text of at most **10,000 characters**; this explicit
anti-abuse limit was not present in the original implementation. Existing clients
depending on unsafe coercion, unrestricted messages or out-of-range inputs need
to handle these errors; compatibility is not claimed for those cases.

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

The container gate also verifies the standard Python 3.14 interpreter and starts
the actual production entrypoint, including SSH and Gunicorn's threaded workers.
A bounded HTTP request must render the password-reset form with its supplied
token. This startup smoke uses test configuration and a container-local MongoDB
URI; rendering the form does not access MongoDB, send email, or download a model.
The smoke container is logged and removed on both success and failure. Full API
behavior and readiness are covered separately against both database backends.

To also block merging failing PRs, configure the repository's `main` branch
ruleset/protection to require the `Checks / Quality gate` status check after its
first run. Workflow dependencies gate deployment; they do not themselves change
GitHub branch-protection settings.

The container uses the official `python:3.14-slim` image from Docker Hub, not a
Microsoft mirror or Azure's built-in Python stack.
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
   is required. The 32-character check is a startup policy, **not** automatic key
   rotation: strong existing values remain unchanged. Short/missing legacy
   settings require an operator-managed upgrade; there is no zero-configuration
   production compatibility claim. Do not rotate keys merely to deploy this code.
3. Set `SEND_GRID_KEY` for email delivery. Missing configuration fails explicitly;
   development/tests do not silently report successful delivery.
4. Confirm mobile clients handle refresh, explicit validation/overload errors,
   deletion retries and the documented input boundaries before promotion. Retire
   all old writers before enabling the deletion admission protocol; an older
   worker cannot honor its marker. New fields default safely on existing users;
   no bulk user rewrite or password/token invalidation is required.
