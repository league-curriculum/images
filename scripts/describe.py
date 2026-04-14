"""Describe images using Claude vision API."""

import anthropic
import base64
import io
import json
import yaml
from pathlib import Path
from PIL import Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

CATEGORIES = {
    'action': (
        "Action shots showing students engaged in activities, demonstrating "
        "that the League is fun and active."
    ),
    'cards': (
        "Adornments for classes on the website. Fairly generic representations "
        "of a class or program."
    ),
    'classes': (
        "Images specific to individual classes, not the whole category but "
        "particular courses."
    ),
    'github': (
        "Screenshots for websites or instructions describing how to use GitHub. "
        "Many are images of particular features of the GitHub website."
    ),
    'logos': (
        "Logos for The League. Use these anywhere logos are required."
    ),
    'memes': (
        "Meme images used in class where students program overlaying text "
        "over images to make memes."
    ),
    'microbit': (
        "Images for websites, instructions, and classes describing how to use "
        "the micro:bit MakeCode site."
    ),
    'misc': "Miscellaneous images.",
    'mkt': (
        "Marketing photos. These tend to be vetted as most useful, so they are "
        "high quality and used frequently."
    ),
    'module-navigation': (
        "Module navigation images for a particular class, specifically the Java "
        "curriculum using CodeSpaces Motors."
    ),
    'motors': (
        "Images for the Motors clinic. These may be deprecated as content has "
        "been moved into the Motors website."
    ),
    'p3logos': (
        "Third-party partner logos (P3 = third party), such as GitHub, "
        "Facebook, or other organizations."
    ),
    'python': "Images used in the Python curriculum.",
    'robots': (
        "Pictures of Cutebots, robots, and other kinds of robots. Use anytime "
        "robot pictures are needed."
    ),
    'stock': "Stock photography.",
    'vscode': (
        "Small images of VS Code features for instructions on how to use "
        "VS Code."
    ),
}

SYSTEM_PROMPT = """\
You are an image analyst. You will be shown an image and must return a JSON object describing it.

The image belongs to a youth coding nonprofit called "The League of Amazing Programmers" (or just "The League"). Keep that context in mind when interpreting what you see.

Return ONLY valid JSON with exactly this structure (no markdown fencing):
{
  "description": "A 2-4 sentence description of what the image shows.",
  "flags": {
    "person_1": false,
    "person_n": false,
    "teaching": false,
    "screenshot": false,
    "logo": false,
    "robot": false,
    "hardware": false,
    "action": false,
    "illustration": false,
    "programming": false,
    "group_photo": false,
    "product_photo": false,
    "duplicate": false,
    "stock": false,
    "presentation": false,
    "building": false,
    "outdoor": false,
    "event": false
  }
}

Flag definitions:
- person_1: Exactly one person is visible
- person_n: Multiple people are visible
- teaching: Shows a student-instructor dynamic
- screenshot: Is a screenshot (whole or partial) of software/website
- logo: Contains or is a logo
- robot: Shows a robot
- hardware: Shows hardware (including robots, circuit boards, electronics)
- action: Shows a person involved in an activity (building, soldering, programming, etc.)
- illustration: Is a drawn/vector illustration rather than a photograph
- programming: Shows someone programming or at a computer coding
- group_photo: A posed group photo (people facing camera, smiling)
- product_photo: A product shot on a clean background
- duplicate: Appears to be a crop/resize/variant of another common image (mark true if it looks like a generic/reused image)
- stock: Appears to be stock photography rather than authentic org photos
- presentation: Shows someone giving a presentation or speech
- building: Shows a building or architectural exterior
- outdoor: Photo was taken outdoors
- event: From a specific event (hackathon, discovery day, ceremony, etc.)

Set each flag to true or false. Be accurate and conservative — only set true when clearly applicable.
"""

MAX_BYTES = 4_500_000


def get_media_type(ext: str) -> str:
    return {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }[ext.lower()]


def yaml_path_for_image(image_path: Path) -> Path:
    """Return the YAML path for a given image. Handles name collisions."""
    base_yaml = image_path.with_suffix('.yaml')
    siblings = [
        f for f in image_path.parent.iterdir()
        if f.suffix.lower() in IMAGE_EXTENSIONS
        and f.stem == image_path.stem
        and f != image_path
    ]
    if siblings and any(s < image_path for s in sorted(siblings)):
        ext_tag = image_path.suffix.lstrip('.').lower()
        return image_path.with_name(f"{image_path.stem}_{ext_tag}.yaml")
    return base_yaml


def load_and_resize(image_path: Path) -> tuple[str, str]:
    """Load image, resize if needed to fit under API limit."""
    with open(image_path, 'rb') as f:
        raw = f.read()

    b64 = base64.standard_b64encode(raw).decode('utf-8')
    media_type = get_media_type(image_path.suffix)

    if len(b64) <= MAX_BYTES:
        return b64, media_type

    img = Image.open(image_path)
    if hasattr(img, 'n_frames') and img.n_frames > 1:
        img.seek(0)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    for scale in [0.75, 0.5, 0.35, 0.25]:
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format='JPEG', quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode('utf-8')
        if len(b64) <= MAX_BYTES:
            return b64, 'image/jpeg'

    resized = img.resize((800, int(800 * img.height / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format='JPEG', quality=70)
    b64 = base64.standard_b64encode(buf.getvalue()).decode('utf-8')
    return b64, 'image/jpeg'


def describe_image(client: anthropic.Anthropic, image_path: Path, category: str) -> dict:
    """Send image to Claude and get structured description back."""
    image_data, media_type = load_and_resize(image_path)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"Describe this image. It is in the '{category}' category "
                        f"({CATEGORIES.get(category, 'no description')})."
                    ),
                },
            ],
        }],
    )

    text = message.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        text = text.rsplit('```', 1)[0]
        text = text.strip()

    return json.loads(text)


def write_yaml(base: Path, image_path: Path, yaml_out: Path, result: dict, category: str):
    """Write the YAML description file."""
    rel_path = image_path.relative_to(base)
    doc = {
        'image': {
            'name': image_path.name,
            'path': str(rel_path),
        },
        'category': category,
        'description': result['description'],
        'flags': result['flags'],
    }
    with open(yaml_out, 'w') as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False, width=80)


def write_category_yaml(dir_path: Path, category: str):
    """Write category.yaml for a directory."""
    cat_file = dir_path / 'category.yaml'
    if cat_file.exists():
        return
    doc = {
        'category': category,
        'description': CATEGORIES.get(category, 'No description available.'),
    }
    with open(cat_file, 'w') as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False, width=80)
    print(f"  Created category.yaml for {category}")


def find_images(dir_path: Path) -> list[Path]:
    """Find all image files in a directory (non-recursive)."""
    return sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def process_directory(client: anthropic.Anthropic, base: Path, dir_path: Path, category: str):
    """Process all images in a directory."""
    images = find_images(dir_path)
    if not images:
        return

    print(f"\n=== {category}/ ({len(images)} images) ===")
    write_category_yaml(dir_path, category)

    skipped = 0
    processed = 0
    errors = 0

    for img in images:
        ypath = yaml_path_for_image(img)
        if ypath.exists():
            skipped += 1
            continue

        try:
            print(f"  Processing: {img.name} ...", end=" ", flush=True)
            result = describe_image(client, img, category)
            write_yaml(base, img, ypath, result, category)
            processed += 1
            print("done")
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}")

    print(f"  Summary: {processed} processed, {skipped} skipped, {errors} errors")


def run_describe(base: Path, categories: list[str] | None):
    """Entry point for the describe command."""
    import os
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        print("No ANTHROPIC_API_KEY set — skipping describe step.")
        return

    client = anthropic.Anthropic()

    dirs_to_process = categories if categories else sorted(CATEGORIES.keys())

    for category in dirs_to_process:
        dir_path = base / category
        if dir_path.is_dir():
            process_directory(client, base, dir_path, category)
        else:
            print(f"Warning: directory '{category}' not found, skipping")

    print("\nDescribe complete!")
