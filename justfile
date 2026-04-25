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

# Build the site and serve it locally (opens browser)
serve port="8000":
    uv run mkimg serve --port {{ port }}
