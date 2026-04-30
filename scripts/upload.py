"""Import all images and metadata into MediaCMS.

Maps the local catalog onto MediaCMS:
  - top-level dirs (`python`, `robots`, ...) -> Categories (must pre-exist on server)
  - flag names that are True on any image  -> Tags (auto-created on assignment)
  - per-image YAML description             -> media description
  - filename stem                          -> media title

Reads MEDIACMS_API and MEDIACMS_API_TOKEN from .env.

Categories are read-only via the REST API and must be pre-created on the server
(admin UI or Django fixture). Tags are get-or-created server-side when assigned
via bulk_actions. State is tracked in data/mediacms_state.json so re-runs skip
already-uploaded images.
"""

import json
import os
import sys
from pathlib import Path

import requests
import yaml

SKIP_DIRS = {'.git', '.venv', '__pycache__', 'data', 'scripts', 'templates',
             'node_modules', 'old_classes', '_site', 'cards'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
STATE_FILENAME = 'mediacms_state.json'


def normalize_tag(title: str) -> str:
    """Match MediaCMS Tag.save() normalization (helpers.get_alphanumeric_only)."""
    return ''.join(c for c in title if c.isalnum()).lower()[:100]


def load_env(base: Path) -> dict:
    env_file = base / '.env'
    out = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k in ('MEDIACMS_API', 'MEDIACMS_API_TOKEN'):
        if k in os.environ:
            out[k] = os.environ[k]
    return out


def api_base(env: dict) -> str:
    raw = env.get('MEDIACMS_API', '').rstrip('/')
    if not raw:
        raise SystemExit("MEDIACMS_API is not set in .env")
    # Drop /swagger or any trailing path; we want the host root
    if raw.endswith('/swagger'):
        raw = raw[:-len('/swagger')]
    return raw


def auth_headers(env: dict) -> dict:
    token = env.get('MEDIACMS_API_TOKEN')
    if not token:
        raise SystemExit("MEDIACMS_API_TOKEN is not set in .env")
    return {'Authorization': f'Token {token}', 'Accept': 'application/json'}


def walk_catalog(base: Path):
    """Yield (category_name, category_description, [(image_path, title, description, [tags])])."""
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith('.'):
            continue
        cat_file = d / 'category.yaml'
        if not cat_file.exists():
            continue
        with open(cat_file) as f:
            cat_data = yaml.safe_load(f) or {}
        category_name = cat_data.get('category', d.name)
        category_description = cat_data.get('description', '')

        described = {}
        for yf in sorted(d.glob('*.yaml')):
            if yf.name == 'category.yaml':
                continue
            try:
                doc = yaml.safe_load(yf.read_text())
            except yaml.YAMLError as e:
                print(f"  warn: failed to parse {yf}: {e}", file=sys.stderr)
                continue
            if not doc or 'image' not in doc:
                continue
            described[doc['image']['name']] = doc

        items = []
        for img in sorted(f for f in d.iterdir()
                          if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS):
            doc = described.get(img.name, {})
            description = doc.get('description', '') or ''
            flags = doc.get('flags', {}) or {}
            tags = sorted({normalize_tag(name) for name, on in flags.items() if on and normalize_tag(name)})
            title = img.stem
            items.append((img, title, description, tags))

        yield category_name, category_description, items


def collect_taxonomy(base: Path):
    """Return ({category: description}, set(tags))."""
    categories = {}
    tags = set()
    for cat, cat_desc, items in walk_catalog(base):
        categories[cat] = cat_desc
        for _, _, _, tag_list in items:
            tags.update(tag_list)
    return categories, tags


def fetch_remote_categories(api: str, headers: dict) -> dict:
    """Fetch existing categories from the API. Returns {title: uid}."""
    out = {}
    url = f"{api}/api/v1/categories"
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        body = r.json()
        results = body if isinstance(body, list) else body.get('results', [])
        for c in results:
            uid = c.get('uid') or c.get('id')
            title = c.get('title')
            if title and uid:
                out[title] = uid
        url = body.get('next') if isinstance(body, dict) else None
    return out


def load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {}


def save_state(state_path: Path, state: dict):
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def upload_image(api: str, headers: dict, img_path: Path, title: str, description: str) -> str:
    """Upload one image. Returns friendly_token."""
    with open(img_path, 'rb') as f:
        files = {'media_file': (img_path.name, f)}
        data = {'title': title, 'description': description}
        r = requests.post(f"{api}/api/v1/media", headers=headers, files=files, data=data, timeout=120)
    r.raise_for_status()
    return r.json()['friendly_token']


def bulk_action(api: str, headers: dict, payload: dict):
    r = requests.post(f"{api}/api/v1/media/user/bulk_actions", headers={**headers, 'Content-Type': 'application/json'},
                      data=json.dumps(payload), timeout=60)
    if not r.ok:
        raise RuntimeError(f"bulk action failed {r.status_code}: {r.text}")
    return r.json()


def run_upload(base: Path, dry_run: bool = False, only_categories=None,
               exclude_categories=None, limit: int = 0):
    env = load_env(base)
    api = api_base(env)
    headers = auth_headers(env)

    print(f"MediaCMS at {api}")

    categories_map, all_tags = collect_taxonomy(base)
    if only_categories:
        only = set(only_categories)
        categories_map = {k: v for k, v in categories_map.items() if k in only}
    if exclude_categories:
        excl = set(exclude_categories)
        categories_map = {k: v for k, v in categories_map.items() if k not in excl}

    print(f"Categories: {len(categories_map)}  Tags: {len(all_tags)}")

    if dry_run:
        remote_cats = {c: 'DRY-UID' for c in categories_map}
    else:
        print("Fetching existing categories from server ...")
        remote_cats = fetch_remote_categories(api, headers)
        print(f"  found {len(remote_cats)} on server")
        missing = [c for c in categories_map if c not in remote_cats]
        if missing:
            raise SystemExit(
                f"Categories missing on server (create via admin first): {missing}"
            )

    state_path = base / 'data' / STATE_FILENAME
    state = load_state(state_path)

    uploaded = 0
    skipped = 0
    failed = 0

    for cat, cat_desc, items in walk_catalog(base):
        if cat not in categories_map:
            continue
        cat_uid = remote_cats.get(cat)
        if not cat_uid:
            print(f"  warn: no UID for category {cat}, skipping")
            continue
        print(f"\n=== {cat} ({len(items)} images) ===")

        for img, title, description, tags in items:
            rel = str(img.relative_to(base))
            entry = state.get(rel)
            if entry and entry.get('friendly_token'):
                skipped += 1
                continue

            if limit and uploaded >= limit:
                print(f"  (limit {limit} reached)")
                save_state(state_path, state)
                _print_summary(uploaded, skipped, failed)
                return

            if dry_run:
                print(f"  [dry] {rel}  title={title!r} tags={tags}")
                uploaded += 1
                continue

            try:
                token = upload_image(api, headers, img, title, description)
            except Exception as e:
                print(f"  FAIL upload {rel}: {e}")
                failed += 1
                continue

            try:
                bulk_action(api, headers, {
                    'media_ids': [token], 'action': 'add_to_category',
                    'category_uids': [cat_uid],
                })
                if tags:
                    bulk_action(api, headers, {
                        'media_ids': [token], 'action': 'add_tags',
                        'tag_titles': tags,
                    })
            except Exception as e:
                print(f"  WARN metadata for {rel} ({token}): {e}")

            state[rel] = {
                'friendly_token': token,
                'category': cat,
                'tags': tags,
                'title': title,
            }
            uploaded += 1
            print(f"  + {rel} -> {token}")
            if uploaded % 10 == 0:
                save_state(state_path, state)

    save_state(state_path, state)
    _print_summary(uploaded, skipped, failed)


def _print_summary(uploaded, skipped, failed):
    print(f"\nDone. uploaded={uploaded} skipped={skipped} failed={failed}")
