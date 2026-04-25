# Curriculum Images

This repo holds images used in League curriculum websites. Each top-level
directory (`action`, `classes`, `logos`, `python`, `robots`, etc.) is a
category of images. Browse the published catalog at:

  [http://images.jointheleague.org](http://images.jointheleague.org)

[Visit the repo](https://github.com/league-curriculum/images) or
<a href="https://codespaces.new/league-curriculum/images" target="_blank">Open in Codespaces</a>.

## How it works

The repo ships with a small CLI called `mkimg` (see [scripts/cli.py](scripts/cli.py))
that builds the catalog site in three steps:

1. **describe** — sends every undescribed image to the Claude vision API and
   writes a sibling `.yaml` file with the title, description, and tags. Images
   that already have a `.yaml` are skipped, so this is cheap to re-run.
2. **compile** — walks every category directory, reads `category.yaml` and the
   per-image YAML files, and merges them into [data/catalog.json](data/catalog.json).
3. **index** — renders the HTML catalog into `_site/` from the Jinja templates
   in [templates/](templates/).

A GitHub Actions workflow ([.github/workflows/build.yml](.github/workflows/build.yml))
runs the same three steps on every push to `master`, copies the image
directories into `_site/`, and deploys the result to GitHub Pages at
`images.jointheleague.org`. The `ANTHROPIC_API_KEY` repo secret is what lets
the workflow describe new images automatically.

## Adding new images

The normal workflow is:

1. Drop image files into the appropriate category directory (e.g. `action/`,
   `robots/`). If you need a new category, make a new directory and add a
   `category.yaml` like the existing ones.
2. Commit and push to `master`.
3. The GitHub Action will describe any new images, regenerate the catalog,
   and redeploy the site. A minute or two later the new images show up at
   [images.jointheleague.org](http://images.jointheleague.org), and you can
   grab the URL from there.

That's it for the common case — you don't have to run anything locally.

## Running it locally

If you want to preview changes before pushing, or describe images without
waiting on CI:

```sh
# One-shot: describe new images, compile, and build the site
just build

# Individual steps
just describe              # all categories
just describe action logos # just these categories
just compile
just index

# Preview at http://localhost:8000/_site/
just dev
```

The `describe` step needs `ANTHROPIC_API_KEY` set in your environment.
`compile` and `index` do not.

## Categories

<!-- start generated content -->

- [/classes](/classes/README.md)
- [/github](/github/README.md)
- [/logos](/logos/README.md)
- [/memes](/memes/README.md)
- [/microbit](/microbit/README.md)
- [/misc](/misc/README.md)
- [/mkt](/mkt/README.md)
- [/module-navigation](/module-navigation/README.md)
- [/motors](/motors/README.md)
- [/p3logos](/p3logos/README.md)
- [/python](/python/README.md)
- [/robots](/robots/README.md)
- [/stock](/stock/README.md)
- [/vscode](/vscode/README.md)
