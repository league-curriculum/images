# League Image Catalog

# Run the full build pipeline: describe, compile, index
build:
    uv run mkimg build

# Describe images using Claude vision (skips already-described)
describe *ARGS:
    uv run mkimg describe {{ ARGS }}

# Compile YAML descriptions into data/catalog.json
compile:
    uv run mkimg compile

# Generate HTML index pages from catalog data
index:
    uv run mkimg index

# Start a local dev server to preview the catalog
dev port="8000":
    @echo "Serving at http://localhost:{{ port }}/_site/"
    uv run python -m http.server {{ port }}
