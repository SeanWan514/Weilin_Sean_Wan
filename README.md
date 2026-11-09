# Weilin Sean Wan personal website

A responsive academic website for Fall 2027 Ph.D. outreach, with sakura and coral pink accents. Research leads the homepage and has five detailed project pages. Compact personal-photo galleries add context on Life and Community without displacing the academic work.

The Python static-site generator produces 13 HTML pages from structured content, CSS, and JavaScript. This is a local build prepared for GitHub Pages; it has not been published.

## Requirements and local preview

Building, validating, and serving the site require Python 3.9 or later and its standard library. There are no frontend dependencies or package-install steps. Pillow is optional and is needed only to regenerate the personal-photo exports from private originals.

Run these commands from this folder:

```sh
python3 scripts/build.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open <http://127.0.0.1:8765/>. Stop the server with Ctrl+C.

The build creates a clean staging directory, copies public assets, generates the pages, and runs the validator before replacing `docs/`. A generation or validation failure leaves the previous working build intact. A successful clean build also removes stale generated files.

To validate the existing output separately:

```sh
python3 scripts/validate.py
```

The validator checks document structure, duplicate IDs, local links and fragments, image and responsive-image paths, CSS asset references, and referenced accessibility IDs. It reports errors and exits unsuccessfully if a check fails. It does not verify external URLs, factual claims, or browser rendering; review the rendered site after content or layout changes.

## Navigation and image viewing

Pages, navigation, and image links work without JavaScript. All research and timeline entries remain visible when filtering is unavailable. JavaScript adds the mobile menu, research and timeline filters, and an image-viewing dialog for photos and conceptual research covers.

The dialog supports keyboard navigation, previous/next controls within a gallery, Escape to close, and focus restoration to the opening link. A direct image link remains the fallback when the dialog cannot open.

## Update content

- `content/site.json`: public URL, email, display name, and GitHub profile.
- `content/research.json`: five research pages, authors, dates, statuses, findings, and paper/code links.
- `content/research-covers.json`: conceptual illustration paths, alt text, and explanatory captions.
- `content/experience.json`: professional roles, product projects, service, teaching, education, awards, news, and timeline.
- `content/life.json`: personal interests, running records, photo captions, and alt text.
- `content/media.json`: photo dimensions, default and enlarged-image paths, and responsive variants.
- `assets/research/`: five distinct SVG research covers, with descriptive titles and labels sized for the larger cards and full-size view.
- `assets/photos/`: optimized public exports of the 16 supplied personal and community photos.
- `assets/images/sean-wan-portrait.jpg`: the optimized 800 × 1200 portrait used on the homepage and in social previews.
- `assets/files/Sean-Wan-CV.pdf`: the supplied academic CV, copied without modification.
- `scripts/build.py`: page structure and homepage prose.
- `scripts/validate.py`: checks for generated pages and local references.
- `assets/style.css`: typography, pink palette, responsive layouts, compact galleries, and dialog styling.
- `assets/site.js`: progressively enhanced navigation, filters, and image viewing.

Edit the source content rather than generated HTML. Run the build after changes, then include the updated `docs/` output when publishing.

## Personal-photo processing

The 16 personal and community photos use conventional image processing. Exports preserve aspect ratio, are not upscaled, and have a maximum long edge of 1600 pixels. Responsive JPEG variants are generated where the source resolution supports them. Existing color profiles are retained, while EXIF/GPS and stale orientation metadata are omitted from exports.

After EXIF orientation normalization, `orientation-2026` and `peer-yuanling` received a 180-degree rotation. Only `running-track` received an exposure adjustment: a uniform brightness multiplier of 1.06. These 16 photos were not processed with generative AI, face retouching, object removal, or synthetic detail.

The homepage portrait is a separate, previously AI-edited asset. Its existing edited PNG was resized and JPEG-optimized to 800 × 1200 pixels and 165,758 bytes, with no new AI modifications. The original portrait and earlier edited PNG are preserved in `private/`; only the optimized JPEG is public.

The optional `scripts/prepare_photos.py` workflow requires Pillow, `private/photo-sources.json`, and the corresponding original files. It writes the public JPEG variants and updates `content/media.json`, while checking that the originals remain unchanged. After restoring those private inputs in a local checkout, run:

```sh
python3 scripts/prepare_photos.py
python3 scripts/build.py
```

All source-photo originals, the earlier edited portrait PNG, the private source manifest, and processing notes are preserved in `private/` and excluded from publication and the distributable package. The package includes the ready-to-use public exports, so normal builds do not require Pillow or the private originals. Photo regeneration will not work from the package alone until those private inputs are restored.

## Content authority

The PDF CV supplies the academic baseline. Sean's confirmed table overrides role titles, dates, and responsibilities. Liberata is separated into Product Manager, July 2025–May 2026, and Machine Learning Engineer / Telemetry Team Lead, May 2026–Present. Covestro and The Climate App use Product Manager. No compensation figures are included.

The downloadable PDF remains the original supplied file. It has not been rewritten to reflect the later separation of Liberata appointments. Replace it with an updated academic CV and rebuild if that distinction should also appear in the PDF.

Research workshop affiliations and manuscripts in preparation are explicit. No acceptance dates were inferred. The SVG covers explain the research concepts; they are not empirical figures or reported results. Their captions distinguish illustrative assembly, token, matrix, and portfolio patterns from measured evidence.

## Publish with GitHub Pages

The configured repository is <https://github.com/SeanWan514/Weilin_Sean_Wan>.

1. Add the source and generated `docs/` directory to that repository, excluding `private/` and other local-only files.
2. In Settings → Pages, select **Deploy from a branch**, then **main** and **/docs**.
3. The expected project URL is <https://seanwan514.github.io/Weilin_Sean_Wan/>.

The configured public URL is a deployment target, not confirmation that deployment has occurred. Internal navigation and assets use relative paths, allowing the build to work under the project path or at a user-site root.

If the repository becomes `seanwan514.github.io`, change `public_url` in `content/site.json` to `https://seanwan514.github.io`, rebuild, and publish. That setting controls canonical and social-preview URLs. GitHub publication and repository renaming have not been performed by this local build.
