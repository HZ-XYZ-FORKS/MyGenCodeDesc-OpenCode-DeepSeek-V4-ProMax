#!/usr/bin/env python3
import subprocess, json, os, random, shutil
from pathlib import Path
from datetime import datetime, timedelta

random.seed(42)

BASE = Path(os.environ.get("WORK_DIR", "."))
REPO = BASE / "repo"
GCD_V4 = BASE / "gcd-v26.04"
GCD_V3 = BASE / "gcd-v26.03"
PATCHES = BASE / "patches"
SVN_REPO = BASE / "svn_repo"
SVN_CO = BASE / "svn_checkout"
SVN_GCD = BASE / "gcd-svn"
SVN_PATCHES = BASE / "svn-patches"

REPO_URL = f"file://{REPO.resolve()}"

FILES = {
    "main.py":      "Entry point and routing",
    "models.py":    "Data models and ORM definitions",
    "handlers.py":  "Request handlers and business logic",
    "utils.py":     "Utility functions and helpers",
    "auth.py":      "Authentication and authorization",
    "db.py":        "Database connection and query layer",
    "config.py":    "Configuration and environment",
    "tests/test_auth.py": "Test suite for auth",
}

DEVS = [
    {"name": "dev0", "email": "dev0@team.io", "ai_ratio": 85},
    {"name": "dev1", "email": "dev1@team.io", "ai_ratio": 80},
    {"name": "dev2", "email": "dev2@team.io", "ai_ratio": 75},
    {"name": "dev3", "email": "dev3@team.io", "ai_ratio": 70},
    {"name": "dev4", "email": "dev4@team.io", "ai_ratio": 50},
    {"name": "dev5", "email": "dev5@team.io", "ai_ratio": 45},
    {"name": "dev6", "email": "dev6@team.io", "ai_ratio": 40},
    {"name": "dev7", "email": "dev7@team.io", "ai_ratio": 15},
    {"name": "dev8", "email": "dev8@team.io", "ai_ratio": 10},
    {"name": "dev9", "email": "dev9@team.io", "ai_ratio": 5},
]

BASE_TIME = datetime(2026, 1, 1, 9, 0, 0)
commit_seq = 0

def git(*args, **kw):
    return subprocess.run(["git"] + list(args), cwd=str(REPO),
                          capture_output=True, text=True, check=True, **kw).stdout.strip()

def svn(*args, **kw):
    return subprocess.run(["svn"] + list(args), cwd=str(SVN_CO) if "cwd" not in kw else None,
                          capture_output=True, text=True, check=True, **kw).stdout.strip()

def next_ts(add_hours=0, add_days=0):
    global commit_seq
    t = BASE_TIME + timedelta(days=add_days, hours=add_hours + commit_seq * 2 + random.randint(0, 4))
    commit_seq += 1
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def pick_dev():
    return random.choice(DEVS)

def commit_git(msg, files_to_modify, date_str):
    dev = pick_dev()
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = dev["name"]
    env["GIT_AUTHOR_EMAIL"] = dev["email"]
    env["GIT_COMMITTER_NAME"] = dev["name"]
    env["GIT_COMMITTER_EMAIL"] = dev["email"]
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    for fname, content in files_to_modify.items():
        (REPO / fname).write_text(content)

    subprocess.run(["git", "add", "-A"], cwd=str(REPO), capture_output=True, text=True, env=env)
    subprocess.run(["git", "commit", "-m", msg], cwd=str(REPO), capture_output=True, text=True, env=env)
    rev = git("rev-parse", "HEAD")
    return rev, dev, files_to_modify

def gen_ratio(n_lines, ai_pct, gen_method="vibeCoding"):
    ratios = []
    for i in range(n_lines):
        if random.random() < ai_pct / 100.0:
            ratios.append(random.choice([100, 100, 100, 95, 90, 80]))
        else:
            ratios.append(0)
    return ratios

def read_file_lines(fname):
    p = REPO / fname
    if not p.exists():
        return []
    return p.read_text().split("\n")

def build_gendesc(rev, ts, commit_files, dev):
    detail_v4 = []
    detail_v3 = []
    total_adds = 0

    for fname, _ in commit_files.items():
        if not fname.endswith(".py"):
            continue
        after_lines = read_file_lines(fname)

        entries = []
        ratios = gen_ratio(len(after_lines), dev["ai_ratio"])
        for i, line in enumerate(after_lines):
            # Conservatively emit add entries for each line in modified files
            gr = ratios[i] if i < len(ratios) else 0
            entries.append({
                "changeType": "add",
                "lineLocation": i + 1,
                "genRatio": gr,
                "genMethod": "vibeCoding" if gr >= 70 else ("codeCompletion" if gr > 0 else "Manual"),
                "blame": {
                    "revisionId": rev, "originalFilePath": fname,
                    "originalLine": i + 1, "timestamp": ts,
                },
            })
            total_adds += 1

        if entries:
            detail_v4.append({"fileName": fname, "codeLines": entries})
            v3_entries = [
                {"lineLocation": e["lineLocation"], "genRatio": e["genRatio"], "genMethod": e["genMethod"]}
                for e in entries if e.get("changeType") == "add"
            ]
            if v3_entries:
                detail_v3.append({"fileName": fname, "codeLines": v3_entries})

    record_v4 = {
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.04",
        "codeAgent": "DemoCodeAgent",
        "REPOSITORY": {
            "vcsType": "git", "repoURL": REPO_URL, "repoBranch": "main",
            "revisionId": rev, "revisionTimestamp": ts,
        },
        "SUMMARY": {
            "totalCodeLines": total_adds,
            "fullGeneratedCodeLines": sum(1 for df in detail_v4 for e in df.get("codeLines", []) if e.get("genRatio", 0) == 100),
            "partialGeneratedCodeLines": sum(1 for df in detail_v4 for e in df.get("codeLines", []) if 0 < e.get("genRatio", 0) < 100),
            "totalDocLines": 0, "fullGeneratedDocLines": 0, "partialGeneratedDocLines": 0,
        },
        "DETAIL": detail_v4,
    }
    (GCD_V4 / f"{rev}.json").write_text(json.dumps(record_v4, indent=2))

    if detail_v3:
        record_v3 = {
            "protocolName": "generatedTextDesc",
            "protocolVersion": "26.03",
            "codeAgent": "DemoCodeAgent",
            "REPOSITORY": {"vcsType": "git", "repoURL": REPO_URL, "repoBranch": "main", "revisionId": rev},
            "SUMMARY": {
                "totalCodeLines": sum(len(e.get("codeLines", [])) for e in detail_v3),
                "fullGeneratedCodeLines": sum(1 for df in detail_v3 for e in df.get("codeLines", []) if e.get("genRatio", 0) == 100),
                "partialGeneratedCodeLines": sum(1 for df in detail_v3 for e in df.get("codeLines", []) if 0 < e.get("genRatio", 0) < 100),
                "totalDocLines": 0, "fullGeneratedDocLines": 0, "partialGeneratedDocLines": 0,
            },
            "DETAIL": detail_v3,
        }
        (GCD_V3 / f"{rev}.json").write_text(json.dumps(record_v3, indent=2))


def build_demo_repo():
    for d in [REPO, GCD_V4, GCD_V3, PATCHES]:
        d.mkdir(parents=True, exist_ok=True)

    git("init", "-b", "main")

    # ====== Week 1: Project scaffolding (heavy AI) ======
    ts = next_ts()

    # C1: Initial project structure by dev0 (85% AI)
    rev, dev, files = commit_git("C1: scaffold project structure — AC: project init", {
        "config.py": "DEBUG = True\nDATABASE_URL = 'sqlite:///:memory:'\nSECRET_KEY = 'dev-key'\nAPI_VERSION = 'v1'\n",
        "main.py": "from config import DEBUG, API_VERSION\nfrom handlers import router\n\napp = None\n\ndef create_app():\n    global app\n    # Initialize application\n    pass\n\ndef run():\n    create_app()\n    # Start server\n    pass\n\nif __name__ == '__main__':\n    run()\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C2: Add utils and DB layer by dev1 (80% AI)
    ts = next_ts()
    rev, dev, files = commit_git("C2: add utility functions and DB layer", {
        "utils.py": "import hashlib\nimport json\nfrom datetime import datetime\n\ndef hash_password(pw: str) -> str:\n    return hashlib.sha256(pw.encode()).hexdigest()\n\ndef to_json(data: dict) -> str:\n    return json.dumps(data, default=str)\n\ndef now() -> str:\n    return datetime.utcnow().isoformat()\n\ndef validate_email(email: str) -> bool:\n    return '@' in email and '.' in email.split('@')[-1]\n",
        "db.py": "from config import DATABASE_URL\n\n_connection = None\n\ndef connect():\n    global _connection\n    # Connect to database\n    pass\n\ndef execute(sql: str, params=None):\n    # Execute SQL statement\n    pass\n\ndef query(sql: str, params=None):\n    # Query and return results\n    return []\n\ndef transaction():\n    # Begin transaction\n    pass\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C3: Auth module by dev2 (75% AI)
    ts = next_ts()
    rev, dev, files = commit_git("C3: add authentication module", {
        "auth.py": "from utils import hash_password, validate_email\n\n_users = {}\n\nclass AuthError(Exception):\n    pass\n\ndef register(email: str, password: str):\n    if not validate_email(email):\n        raise AuthError('Invalid email')\n    if email in _users:\n        raise AuthError('User exists')\n    _users[email] = hash_password(password)\n    return True\n\ndef login(email: str, password: str) -> bool:\n    stored = _users.get(email)\n    if not stored:\n        return False\n    return stored == hash_password(password)\n\ndef get_user(email: str):\n    return {'email': email} if email in _users else None\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C4: Models by dev0 (85% AI)
    ts = next_ts()
    rev, dev, files = commit_git("C4: add data models", {
        "models.py": "from datetime import datetime\nfrom utils import now\n\nclass BaseModel:\n    def __init__(self):\n        self.id = None\n        self.created_at = now()\n        self.updated_at = now()\n\n    def to_dict(self) -> dict:\n        return {\n            'id': self.id,\n            'created_at': self.created_at,\n            'updated_at': self.updated_at,\n        }\n\nclass User(BaseModel):\n    def __init__(self, email: str, name: str = ''):\n        super().__init__()\n        self.email = email\n        self.name = name\n\n    def to_dict(self) -> dict:\n        d = super().to_dict()\n        d.update({'email': self.email, 'name': self.name})\n        return d\n\nclass Post(BaseModel):\n    def __init__(self, title: str, content: str, author_email: str):\n        super().__init__()\n        self.title = title\n        self.content = content\n        self.author_email = author_email\n\n    def to_dict(self) -> dict:\n        d = super().to_dict()\n        d.update({'title': self.title, 'content': self.content, 'author_email': self.author_email})\n        return d\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # ====== Week 2: Feature development (mixed AI-human) ======

    # C5: Handlers by dev3 (70% AI)
    ts = next_ts()
    rev, dev, files = commit_git("C5: add request handlers", {
        "handlers.py": "from models import User, Post\nfrom auth import register, login, get_user\nfrom db import execute, query\nfrom utils import to_json\n\ndef handle_register(email: str, password: str):\n    try:\n        register(email, password)\n        return to_json({'status': 'ok', 'message': 'User registered'})\n    except Exception as e:\n        return to_json({'status': 'error', 'message': str(e)})\n\ndef handle_login(email: str, password: str):\n    if login(email, password):\n        return to_json({'status': 'ok', 'token': 'session-token'})\n    return to_json({'status': 'error', 'message': 'Invalid credentials'})\n\ndef handle_create_post(author_email: str, title: str, content: str):\n    if not get_user(author_email):\n        return to_json({'status': 'error', 'message': 'User not found'})\n    post = Post(title, content, author_email)\n    return to_json({'status': 'ok', 'post': post.to_dict()})\n\ndef handle_list_posts():\n    posts = query('SELECT * FROM posts')\n    return to_json({'status': 'ok', 'posts': posts})\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C6: Dev4 (50% AI) refines config + adds env support
    ts = next_ts()
    rev, dev, files = commit_git("C6: add environment config and validation", {
        "config.py": "import os\n\nDEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\nDATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///:memory:')\nSECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-me')\nAPI_VERSION = 'v1'\nMAX_POSTS_PER_PAGE = int(os.getenv('MAX_POSTS_PER_PAGE', '20'))\nSESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C7: Dev7 (15% AI) fixes a bug in auth — human review
    ts = next_ts()
    rev, dev, files = commit_git("C7: fix auth — hash comparison timing-safe", {
        "auth.py": open(str(REPO / "auth.py")).read().replace(
            "return stored == hash_password(password)",
            "import hmac\n    return hmac.compare_digest(stored, hash_password(password))"
        ),
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C8: Dev1 (80% AI) adds pagination to handlers
    ts = next_ts()
    rev, dev, files = commit_git("C8: add pagination support to handlers", {
        "handlers.py": open(str(REPO / "handlers.py")).read().replace(
            "def handle_list_posts():",
            "def handle_list_posts(page: int = 1):"
        ).replace(
            "posts = query('SELECT * FROM posts')",
            "from config import MAX_POSTS_PER_PAGE\n    offset = (page - 1) * MAX_POSTS_PER_PAGE\n    posts = query('SELECT * FROM posts LIMIT ? OFFSET ?', [MAX_POSTS_PER_PAGE, offset])"
        ).replace(
            "'posts': posts}",
            "'posts': posts, 'page': page}"
        ),
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # ====== Week 3: Bug fixes + refinement ======

    # C9: Feature branch — add password reset
    git("checkout", "-b", "feature-password-reset")
    ts = next_ts()
    rev, dev, files = commit_git("C9: add password reset feature (feature branch)", {
        "auth.py": open(str(REPO / "auth.py")).read() + "\n\ndef reset_password(email: str, new_password: str):\n    if not get_user(email):\n        raise AuthError('User not found')\n    _users[email] = hash_password(new_password)\n    return True\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C10: Merge feature branch
    git("checkout", "main")
    global commit_seq
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = (BASE_TIME + timedelta(days=15, hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    env["GIT_AUTHOR_NAME"] = "dev5"
    env["GIT_AUTHOR_EMAIL"] = "dev5@team.io"
    subprocess.run(["git", "merge", "feature-password-reset", "--no-ff", "-m", "C10: merge password reset — AC: merge blame"],
                   cwd=str(REPO), capture_output=True, text=True, env=env)
    commit_seq += 1

    # C11: Dev8 (10% AI) adds manual test
    ts = next_ts()
    (REPO / "tests").mkdir(exist_ok=True)
    rev, dev, files = commit_git("C11: add manual test for auth module", {
        "tests/test_auth.py": "from auth import register, login, get_user, AuthError\n\ndef test_register_success():\n    assert register('test@example.com', 'password123')\n\ndef test_register_duplicate():\n    try:\n        register('test@example.com', 'password123')\n        assert False, 'Should raise'\n    except AuthError:\n        pass\n\ndef test_login_success():\n    register('login@test.com', 'pass')\n    assert login('login@test.com', 'pass')\n\ndef test_login_wrong_password():\n    register('login2@test.com', 'pass')\n    assert not login('login2@test.com', 'wrong')\n\ndef test_get_user():\n    register('user@test.com', 'pass')\n    u = get_user('user@test.com')\n    assert u is not None\n    assert u['email'] == 'user@test.com'\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C12: Dev2 (75% AI) rewrites auth to use database
    ts = next_ts()
    rev, dev, files = commit_git("C12: refactor auth to use database layer — AC: ownership transfer AI→human→AI", {
        "auth.py": open(str(REPO / "auth.py")).read().replace(
            "_users = {}\n",
            "from db import execute, query\n\ndef _get_stored_hash(email: str) -> str:\n    rows = query('SELECT password_hash FROM users WHERE email = ?', [email])\n    return rows[0][0] if rows else None\n\ndef _store_user(email: str, pw_hash: str):\n    execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', [email, pw_hash])\n"
        ).replace("_users[email] = hash_password(password)", "_store_user(email, hash_password(password))"
        ).replace("_users.get(email)", "_get_stored_hash(email)"
        ).replace("_users[email] = hash_password(new_password)", "_store_user(email, hash_password(new_password))"
        ).replace("_ = _users.get(email)", "_ = _get_stored_hash(email)"
        ).replace("if email in _users:", "if _get_stored_hash(email):"
        ).replace("return _users.get(email)", "return _get_stored_hash(email)"
        ),
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C13: Dev9 (5% AI) cleans up db.py
    ts = next_ts()
    rev, dev, files = commit_git("C13: add connection pool and error handling to db", {
        "db.py": open(str(REPO / "db.py")).read() + "\n\nclass DatabaseError(Exception):\n    pass\n\nclass ConnectionPool:\n    def __init__(self, max_connections=10):\n        self.max = max_connections\n        self.active = 0\n\n    def acquire(self):\n        if self.active >= self.max:\n            raise DatabaseError('Connection pool exhausted')\n        self.active += 1\n\n    def release(self):\n        self.active = max(0, self.active - 1)\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # ====== Week 4: Testing + polish ======

    # C14: Dev6 (40% AI) adds test utilities
    ts = next_ts()
    rev, dev, files = commit_git("C14: add test fixtures and mock helpers", {
        "tests/test_auth.py": open(str(REPO / "tests/test_auth.py")).read() + "\n\n# Test fixtures\nimport pytest\n\n@pytest.fixture\ndef clean_users():\n    # Reset user database before each test\n    from db import execute\n    execute('DELETE FROM users')\n    yield\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C15: Dev0 (85% AI) adds rate limiting to handlers
    ts = next_ts()
    rev, dev, files = commit_git("C15: add rate limiting to auth handlers", {
        "handlers.py": open(str(REPO / "handlers.py")).read().replace(
            "def handle_login(email: str, password: str):",
            "def _check_rate_limit(email: str, max_attempts: int = 5) -> bool:\n    # Simple rate limiter\n    return True\n\ndef handle_login(email: str, password: str):"
        ),
        "utils.py": open(str(REPO / "utils.py")).read() + "\n\ndef rate_limit_key(identifier: str) -> str:\n    return f'rate_limit:{identifier}:{now()[:13]}'\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C16: Rename config.py → settings.py by dev7 (15% AI)
    git("mv", "config.py", "settings.py")
    ts = next_ts()
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "dev7"
    env["GIT_AUTHOR_EMAIL"] = "dev7@team.io"
    env["GIT_AUTHOR_DATE"] = ts
    env["GIT_COMMITTER_NAME"] = "dev7"
    env["GIT_COMMITTER_EMAIL"] = "dev7@team.io"
    env["GIT_COMMITTER_DATE"] = ts
    subprocess.run(["git", "commit", "-m", "C16: rename config.py → settings.py — AC: file rename"],
                   cwd=str(REPO), capture_output=True, text=True, env=env)
    rev = git("rev-parse", "HEAD")
    # No genCodeDesc for pure rename (per spec)
    commit_seq += 1

    # C17: Dev2 (75% AI) refactors handlers — multi-file
    ts = next_ts()
    rev, dev, files = commit_git("C17: refactor handlers — extract route registry", {
        "handlers.py": open(str(REPO / "handlers.py")).read().replace(
            "def handle_register",
            "routes = {}\n\ndef route(path: str):\n    def decorator(fn):\n        routes[path] = fn\n        return fn\n    return decorator\n\ndef handle_register"
        ),
        "main.py": open(str(REPO / "main.py")).read().replace(
            "from config import DEBUG",
            "from settings import DEBUG"
        ).replace(
            "from handlers import router",
            "from handlers import routes"
        ),
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C18: Dev9 (5% AI) adds doc comments
    ts = next_ts()
    current_auth = open(str(REPO / "auth.py")).read()
    rev, dev, files = commit_git("C18: add docstrings to auth module — AC: human edit on AI code", {
        "auth.py": '"""Authentication and authorization module.\n\nProvides user registration, login, password reset,\nand session management backed by database storage.\n"""\n' + current_auth,
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C19: Dev8 (10% AI) deletes unused test fixture
    ts = next_ts()
    rev, dev, files = commit_git("C19: remove test fixture placeholder — AC: file delete", {
        "tests/test_auth.py": open(str(REPO / "tests/test_auth.py")).read().replace(
            "# Test fixtures\nimport pytest\n\n@pytest.fixture\ndef clean_users():\n    # Reset user database before each test\n    from db import execute\n    execute('DELETE FROM users')\n    yield\n",
            ""
        ),
    }, ts)
    build_gendesc(rev, ts, files, dev)

    # C20: Dev4 (50% AI) final polish
    ts = next_ts()
    rev, dev, files = commit_git("C20: final polish — update imports and error messages", {
        "settings.py": "import os\n\nDEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\nDATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///:memory:')\nSECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-me')\nAPI_VERSION = 'v1'\nMAX_POSTS_PER_PAGE = int(os.getenv('MAX_POSTS_PER_PAGE', '20'))\nSESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))\nAPP_NAME = 'MyBackend'\nVERSION = '0.1.0'\n",
    }, ts)
    build_gendesc(rev, ts, files, dev)

    print(f"Git repo: {REPO} ({commit_seq} commits)")

    # Generate patches for AlgB
    commits = git("log", "--topo-order", "--reverse", "--first-parent", "--format=%H").split("\n")
    for rev in commits:
        if not rev: continue
        diff = subprocess.run(["git", "format-patch", "-1", "--stdout", "--unified=3", "--first-parent", rev],
                              cwd=str(REPO), capture_output=True, text=True).stdout
        if diff.strip():
            (PATCHES / f"{rev}.patch").write_text(diff)
    print(f"Patches: {PATCHES}")


def build_svn_repo():
    if not shutil.which("svn"):
        print("SVN not installed, skipping")
        return

    for d in [SVN_REPO, SVN_CO, SVN_GCD, SVN_PATCHES]:
        d.mkdir(parents=True, exist_ok=True)

    if (SVN_REPO / "format").exists():
        print("SVN repo exists, skipping create")
    else:
        svn("admin", "create", str(SVN_REPO))
    svn("checkout", f"file://{SVN_REPO.resolve()}", str(SVN_CO), "--quiet")

    # r1: add main.py
    (SVN_CO / "main.py").write_text("line 1\nline 2\nline 3\nline 4\nline 5\n")
    svn("add", "main.py", "--quiet")
    svn("commit", "-m", "r1: add main.py", "--quiet")
    r1 = svn("info", "--show-item", "revision").strip()

    # r2: modify line 3
    lines = (SVN_CO / "main.py").read_text().split("\n")
    lines[2] = "line 3 - MODIFIED by AI"
    (SVN_CO / "main.py").write_text("\n".join(lines))
    svn("commit", "-m", "r2: modify line 3 (AI rewrite)", "--quiet")
    r2 = svn("info", "--show-item", "revision").strip()

    # r3: add utils.py
    (SVN_CO / "utils.py").write_text("def helper():\n    return 42\n")
    svn("add", "utils.py", "--quiet")
    svn("commit", "-m", "r3: add utils.py", "--quiet")
    r3 = svn("info", "--show-item", "revision").strip()

    svn_url = f"file://{SVN_REPO.resolve()}"

    for rev, fname, gr_val in [(r1, "main.py", 60), (r2, "main.py", 80), (r3, "utils.py", 40)]:
        lines = open(str(SVN_CO / fname)).readlines()
        entries = []
        for i, ln in enumerate(lines):
            gr = random.randint(gr_val - 10, gr_val + 10) if random.random() < 0.7 else 0
            gr = max(0, min(100, gr))
            entries.append({
                "lineLocation": i + 1,
                "genRatio": gr,
                "genMethod": "vibeCoding" if gr > 50 else "Manual",
            })
        data = {
            "protocolVersion": "26.03", "codeAgent": "DemoSVN",
            "REPOSITORY": {"vcsType": "svn", "repoURL": svn_url, "repoBranch": "/trunk", "revisionId": rev},
            "SUMMARY": {"totalCodeLines": len(entries), "fullGeneratedCodeLines": sum(1 for e in entries if e["genRatio"] == 100),
                         "partialGeneratedCodeLines": sum(1 for e in entries if 0 < e["genRatio"] < 100),
                         "totalDocLines": 0, "fullGeneratedDocLines": 0, "partialGeneratedDocLines": 0},
            "DETAIL": [{"fileName": fname, "codeLines": entries}],
        }
        (SVN_GCD / f"{rev}.json").write_text(json.dumps(data, indent=2))
        patch = subprocess.run(["svn", "diff", "-c", rev, svn_url], capture_output=True, text=True).stdout
        if patch.strip():
            (SVN_PATCHES / f"{rev}.patch").write_text(patch)

    print(f"SVN repo: {SVN_REPO} (3 revisions)")
    print(f"SVN gencode: {SVN_GCD}")


if __name__ == "__main__":
    build_demo_repo()
    build_svn_repo()
    print("Done. Run: ./run_demo.sh")
