"""Compile all YAML description files into a single JSON catalog."""

import json
import yaml
from pathlib import Path

SKIP_DIRS = {'.git', '.venv', '__pycache__', 'data', 'scripts', 'templates', 'node_modules'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


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

        # Collect described images from YAML files
        described = {}  # image filename -> entry
        yaml_files = sorted(d.glob('*.yaml'))

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

            described[doc['image']['name']] = image_entry

            for flag_name in doc.get('flags', {}).keys():
                catalog['flags'].add(flag_name)

        # Find all image files, including undescribed ones
        all_images = sorted(
            f for f in d.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )

        undescribed = 0
        for img_file in all_images:
            if img_file.name in described:
                catalog['images'].append(described[img_file.name])
            else:
                catalog['images'].append({
                    'name': img_file.name,
                    'path': str(img_file.relative_to(base)),
                    'category': category_name,
                    'description': '',
                    'flags': {},
                })
                undescribed += 1

        image_count = len(all_images)
        catalog['categories'][category_name]['image_count'] = image_count
        desc_label = f" ({undescribed} undescribed)" if undescribed else ""
        print(f"  {category_name}: {image_count} images{desc_label}")

    catalog['flags'] = sorted(catalog['flags'])

    out_path = data_dir / 'catalog.json'
    with open(out_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    total = len(catalog['images'])
    cats = len(catalog['categories'])
    print(f"\nCompiled {total} images across {cats} categories -> {out_path}")
