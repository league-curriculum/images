"""Generate HTML index pages from compiled catalog data."""

import json
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

SITE_DIR = '_site'


def run_index(base: Path):
    """Generate index.html and per-category HTML pages into _site/."""
    catalog_path = base / 'data' / 'catalog.json'
    if not catalog_path.exists():
        print("Error: data/catalog.json not found. Run 'mkimg compile' first.")
        return

    with open(catalog_path) as f:
        catalog = json.load(f)

    site = base / SITE_DIR
    site.mkdir(exist_ok=True)

    # Copy catalog.json into _site/data/ so the JS search can fetch it
    site_data = site / 'data'
    site_data.mkdir(exist_ok=True)
    shutil.copy2(catalog_path, site_data / 'catalog.json')

    env = Environment(
        loader=FileSystemLoader(str(base / 'templates')),
        autoescape=True,
    )

    categories_list = [
        {
            'name': name,
            'description': info['description'],
            'count': info['image_count'],
        }
        for name, info in sorted(catalog['categories'].items())
    ]

    flags = catalog.get('flags', [])
    all_images = catalog.get('images', [])

    # Prefix image paths with ../ since HTML is in _site/
    for img in all_images:
        img['path'] = '../' + img['path']

    common = {
        'categories': categories_list,
        'flags': flags,
    }

    # Home page
    tmpl = env.get_template('home.html')
    html = tmpl.render(
        title='All Images',
        active_category='index',
        total_images=len(all_images),
        images=all_images,
        **common,
    )
    (site / 'index.html').write_text(html)
    print(f"  Generated index.html ({len(all_images)} images)")

    # Per-category pages
    for cat in categories_list:
        cat_images = [img for img in all_images if img['category'] == cat['name']]
        tmpl = env.get_template('category.html')
        html = tmpl.render(
            title=cat['name'],
            active_category=cat['name'],
            category_name=cat['name'],
            category_description=cat['description'],
            images=cat_images,
            **common,
        )
        (site / f"{cat['name']}.html").write_text(html)
        print(f"  Generated {cat['name']}.html ({len(cat_images)} images)")

    print(f"\nGenerated {1 + len(categories_list)} HTML pages in {SITE_DIR}/")
