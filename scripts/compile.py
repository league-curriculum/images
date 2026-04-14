"""Compile all YAML description files into a single JSON catalog."""

import json
import yaml
from pathlib import Path

SKIP_DIRS = {'.git', '.venv', '__pycache__', 'data', 'scripts', 'templates', 'node_modules'}


def run_compile(base: Path):
    """Walk all category directories and compile YAML into data/catalog.json."""
    data_dir = base / 'data'
    data_dir.mkdir(exist_ok=True)

    catalog = {
        'categories': {},
        'images': [],
        'flags': set(),
    }

    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith('.'):
            continue

        cat_file = d / 'category.yaml'
        if not cat_file.exists():
            continue

        with open(cat_file) as f:
            cat_data = yaml.safe_load(f)

        category_name = cat_data.get('category', d.name)
        catalog['categories'][category_name] = {
            'description': cat_data.get('description', ''),
            'image_count': 0,
        }

        yaml_files = sorted(d.glob('*.yaml'))
        image_count = 0

        for yf in yaml_files:
            if yf.name == 'category.yaml':
                continue

            with open(yf) as f:
                try:
                    doc = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    print(f"  Warning: failed to parse {yf}: {e}")
                    continue

            if not doc or 'image' not in doc:
                continue

            image_entry = {
                'name': doc['image']['name'],
                'path': doc['image']['path'],
                'category': doc.get('category', category_name),
                'description': doc.get('description', ''),
                'flags': doc.get('flags', {}),
            }

            catalog['images'].append(image_entry)
            image_count += 1

            for flag_name in doc.get('flags', {}).keys():
                catalog['flags'].add(flag_name)

        catalog['categories'][category_name]['image_count'] = image_count
        print(f"  {category_name}: {image_count} images")

    catalog['flags'] = sorted(catalog['flags'])

    out_path = data_dir / 'catalog.json'
    with open(out_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    total = len(catalog['images'])
    cats = len(catalog['categories'])
    print(f"\nCompiled {total} images across {cats} categories -> {out_path}")
