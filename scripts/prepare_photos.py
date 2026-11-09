#!/usr/bin/env python3
"""Create responsive, conventionally edited JPEGs from preserved photo originals.

Run with the bundled Python runtime (Pillow is required). Sources are read only;
the script updates assets/photos, content/media.json and the private process note.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "private/photo-sources.json"
MEDIA_MANIFEST = ROOT / "content/media.json"
PHOTO_DIR = ROOT / "assets/photos"
NOTE_PATH = ROOT / "private/photo-processing.txt"
LONG_EDGE_LIMIT = 1600
RESPONSIVE_WIDTHS = (480, 960, 1600)
ROTATIONS = {"orientation-2026": 180, "peer-yuanling": 180}
BRIGHTNESS = {"running-track": 1.06}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_source(record: dict) -> Path:
    """Prefer the preserved local original so a moved checkout remains usable."""
    recorded = Path(record["source"])
    local = ROOT / "private/photo-originals" / recorded.name
    source = local if local.is_file() else recorded
    if not source.is_file():
        raise FileNotFoundError(source)
    return source


def main() -> None:
    sources = json.loads(SOURCE_MANIFEST.read_text())
    media = json.loads(MEDIA_MANIFEST.read_text())
    ids = [record["id"] for record in sources]
    if len(ids) != len(set(ids)) or set(ids) != set(media):
        raise ValueError("Photo source IDs and media IDs must match uniquely.")
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    original_hashes = {}
    report = []
    generated_names = set()
    staged_media = {}

    with tempfile.TemporaryDirectory(prefix="sean-photo-derivatives-") as temporary:
        stage = Path(temporary)
        for record in sources:
            photo_id = record["id"]
            source = resolve_source(record)
            original_hashes[source] = digest(source)
            with Image.open(source) as original:
                native_size = original.size
                icc_profile = original.info.get("icc_profile")
                photo = ImageOps.exif_transpose(original)
                if ROTATIONS.get(photo_id) == 180:
                    # Lossless pixel rearrangement before the JPEG encoding step.
                    photo = photo.transpose(Image.Transpose.ROTATE_180)
                if photo.mode != "RGB":
                    photo = photo.convert("RGB")
                else:
                    photo = photo.copy()

            factor = BRIGHTNESS.get(photo_id, 1.0)
            if factor != 1.0:
                photo = ImageEnhance.Brightness(photo).enhance(factor)

            scale = min(1.0, LONG_EDGE_LIMIT / max(photo.size))
            full_size = (
                max(1, round(photo.width * scale)),
                max(1, round(photo.height * scale)),
            )
            widths = sorted({w for w in RESPONSIVE_WIDTHS if w < full_size[0]} | {full_size[0]})
            variants = []
            variant_report = []
            for width in widths:
                height = max(1, round(width * photo.height / photo.width))
                size = (width, height)
                derivative = photo if size == photo.size else photo.resize(size, Image.Resampling.LANCZOS)
                filename = f"{photo_id}-{width}w.jpg"
                target = stage / filename
                options = {
                    "format": "JPEG",
                    "quality": 94 if photo_id == "flight-log" else 88,
                    "optimize": True,
                    "progressive": True,
                    "subsampling": 0 if photo_id == "flight-log" else 2,
                }
                if icc_profile:
                    options["icc_profile"] = icc_profile
                # Do not copy EXIF/GPS or stale orientation metadata into exports.
                derivative.save(target, **options)
                with Image.open(target) as checked:
                    checked.load()
                    if checked.size != size or checked.format != "JPEG":
                        raise ValueError(f"Invalid derivative: {filename}")
                    if checked.getexif().get(274) not in (None, 1):
                        raise ValueError(f"Unexpected EXIF rotation: {filename}")
                if max(size) > LONG_EDGE_LIMIT or width > photo.width or height > photo.height:
                    raise ValueError(f"Upscaled or oversized derivative: {filename}")
                variants.append({"path": f"/assets/photos/{filename}", "width": width})
                variant_report.append((filename, size, target.stat().st_size))
                generated_names.add(filename)

            default = max((item for item in variants if item["width"] <= 960), key=lambda item: item["width"])
            default_size = next(size for name, size, _ in variant_report if name == Path(default["path"]).name)
            staged_media[photo_id] = {
                **media[photo_id],
                "src": default["path"],
                "full": variants[-1]["path"],
                "width": default_size[0],
                "height": default_size[1],
                "rotation": 0,
                "variants": variants,
            }
            report.append({
                "id": photo_id,
                "source": source,
                "original_size": native_size,
                "original_bytes": source.stat().st_size,
                "rotation": ROTATIONS.get(photo_id, 0),
                "brightness": factor,
                "variants": variant_report,
            })

        for source, before in original_hashes.items():
            if digest(source) != before:
                raise ValueError(f"Preserved original changed: {source}")

        # Only expose the new manifest after every derivative has been verified.
        for filename in generated_names:
            (PHOTO_DIR / filename).write_bytes((stage / filename).read_bytes())
        MEDIA_MANIFEST.write_text(json.dumps(staged_media, ensure_ascii=False, indent=2) + "\n")

    # Delete only known temporary raw copies and this script's obsolete derivatives.
    for record in sources:
        photo_id = record["id"]
        raw_copy = PHOTO_DIR / Path(record["source"]).name
        if raw_copy.is_file() and raw_copy.name not in generated_names:
            raw_copy.unlink()
        pattern = re.compile(rf"{re.escape(photo_id)}-\d+w\.jpg")
        for candidate in PHOTO_DIR.iterdir():
            if candidate.is_file() and pattern.fullmatch(candidate.name) and candidate.name not in generated_names:
                candidate.unlink()

    original_total = sum(item["original_bytes"] for item in report)
    output_total = sum(size for item in report for _, _, size in item["variants"])
    lines = [
        "Personal website photo processing",
        "",
        "Reproduce: run scripts/prepare_photos.py with Python 3 and Pillow.",
        "Preserved originals: private/photo-originals (SHA-256 checked unchanged during processing).",
        "All exports: EXIF transpose, no crop, no upscaling, aspect ratio preserved; longest side <=1600 pixels.",
        "orientation-2026 and peer-yuanling: exactly 180-degree pixel rotation after EXIF normalization.",
        "running-track: uniform brightness multiplier 1.06 after inspection; all other exposure unchanged.",
        "No AI processing, face editing, retouching, object removal, or synthetic detail.",
        "JPEG quality 88, progressive, optimized; flight-log quality 94 with full chroma detail for legibility.",
        "Existing ICC color profiles retained; EXIF/GPS and obsolete orientation metadata omitted from exports.",
        "Responsive widths: 480, 960, 1600 where supported, plus each image's native/capped maximum width.",
        "Manifest src uses the largest export <=960 pixels wide; full uses the largest export; rotation is 0.",
        "Temporary raw public copies removed only after all derivatives were validated.",
        "",
        f"Originals: {original_total:,} bytes across {len(report)} photos.",
        f"All derivative variants: {output_total:,} bytes across {len(generated_names)} JPEG files.",
        f"Aggregate byte reduction versus raw public copies: {(1 - output_total / original_total) * 100:.2f}%.",
        "",
    ]
    for item in report:
        lines.append(f"{item['id']}: original {item['original_size'][0]}x{item['original_size'][1]}, {item['original_bytes']:,} bytes; rotation {item['rotation']}; brightness {item['brightness']}")
        for filename, size, count in item["variants"]:
            lines.append(f"  {filename}: {size[0]}x{size[1]}, {count:,} bytes")
    NOTE_PATH.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[13:17]))
    for item in report:
        filename, size, count = item["variants"][-1]
        print(f"{item['id']}: full {size[0]}x{size[1]}, {count:,} bytes; {len(item['variants'])} variants")


if __name__ == "__main__":
    main()
