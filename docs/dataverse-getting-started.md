# Run MetaDIG-py checks against a Dataverse dataset

This guide shows two practical ways to try MetaDIG-py with a Dataverse installation.

MetaDIG-py expects:
- a metadata XML file (EML preferred), and
- a DataONE System Metadata (sysmeta) XML for that metadata object.

Dataverse doesn't provide DataONE sysmeta, so we generate a small "stub" that contains the few fields MetaDIG-py uses. This is enough to run metadata-only checks; data-oriented checks will simply run with an empty `dataPids` list unless your dataset is also in DataONE.

## Option A: Quick local test (metadata-only)

1) Install MetaDIG-py and dependencies

- Install Poetry if you don't have it: https://python-poetry.org/docs/#installation
- From the repo root:

```sh
poetry install
```

2) Export EML from your Dataverse dataset (automated)

- Use the helper to fetch EML and write a sysmeta stub in one go (replace base URL and DOI):

```sh
poetry run python scripts/dataverse_to_metadig.py \
  --base-url https://your.dataverse.example \
  --persistent-id doi:10.12345/XYZ \
  --api-key $DATAVERSE_KEY \
  --metadata-out /tmp/dataset.xml \
  --sysmeta-out /tmp/sysmeta.xml \
  --authoritative-member-node urn:node:KNB
```

Notes:
- `--api-key` is optional for public datasets.
- If EML export isn't enabled on your Dataverse, you can run the curl exporter manually with `ddi` or `datacite` and still use `scripts/generate_sysmeta_stub.py` to create the stub.

3) (Alternative) Manually create a sysmeta stub

If you exported metadata via another format or manually, you can create a stub directly:

```sh
poetry run python scripts/generate_sysmeta_stub.py \
  --identifier doi:10.12345/XYZ \
  --authoritative-member-node urn:node:KNB \
  --rights-holder "CN=your-user,DC=dataone,DC=org" \
  --file-name dataset.xml \
  --out /tmp/sysmeta.xml
```

- Any valid DataONE member node ID is fine (used only to build a base URL):
  `urn:node:KNB`, `urn:node:ARCTIC`, `urn:node:EDI`, `urn:node:USGS_SDC`, ...
- If your DOI is not in that node, `dataPids` will simply be empty, which is fine for metadata-only checks.

4) Run a single check

Use the sample checks bundled with this repo (metadata-only examples):

```sh
poetry run metadigpy \
  -runcheck \
  -store_path=$(pwd)/hashstore \
  -check_xml=$(pwd)/tests/testdata/checks/resource.license.present-2.0.0.xml \
  -metadata_doc=/tmp/dataset.xml \
  -sysmeta_doc=/tmp/sysmeta.xml
```

5) Run a small suite (optional)

```sh
poetry run metadigpy \
  -runsuite \
  -suite_path=$(pwd)/tests/testdata/FAIR-suite-0.4.0.xml \
  -check_folder=$(pwd)/tests/testdata/checks \
  -metadata_doc=/tmp/dataset.xml \
  -sysmeta_doc=/tmp/sysmeta.xml \
  -store_path=$(pwd)/hashstore
```

Expect some checks to be missing or skipped; the sample suite references more checks than this repo bundles.

## Option B: Include data checks (if your dataset is also in DataONE)

If your Dataverse is a DataONE Member Node (or your dataset has been synced to one):

1) Download the metadata sysmeta from DataONE CN

```sh
curl -L -o /tmp/sysmeta.xml "https://cn.dataone.org/cn/v2/meta/doi:10.12345/XYZ"
```

2) Download the metadata XML (EML) and the dataset zip from your MN or portal

- EML: via CN resolve or your MN portal
- Data files: download and extract to `/tmp/dataset/`

3) Import data + per-object sysmeta into the default hashstore

```sh
poetry run metadigpy \
  -importhashstoredata \
  -sysmeta_doc=/tmp/sysmeta.xml \
  -data_folder=/tmp/dataset
```

4) Run a data suite

```sh
poetry run metadigpy \
  -runsuite \
  -suite_path=/path/to/data-suite.xml \
  -check_folder=/path/to/metadig-checks/python-checks \
  -metadata_doc=/tmp/dataset.xml \
  -sysmeta_doc=/tmp/sysmeta.xml \
  -store_path=$(pwd)/hashstore
```

## Troubleshooting

- EML not available from Dataverse: switch exporter to `ddi` or `datacite`. Some checks may not match.
- HTTP errors when running checks: the tool queries DataONE CN to look up member node base URLs. Make sure you used a valid `--authoritative-member-node` in the stub.
- Data checks failing with missing objects: either skip data checks or complete the import into the hashstore (Option B).

## What MetaDIG-py is and isn't

- It's a helper to run MetaDIG checks locally. It doesn't talk to Dataverse APIs directly.
- You bring the metadata XML and (for data checks) the data files into a local hashstore.
- For production evaluation across many datasets, use the MetaDIG Engine with the full metadig-checks repository.
