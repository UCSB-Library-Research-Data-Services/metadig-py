# Offline Metadata Quality Suite

## Overview

The **Offline Metadata Quality Suite** is a collection of MetaDIG checks designed to work **entirely offline** without requiring network access. This makes it perfect for:

- Local development and testing
- CI/CD pipelines
- Air-gapped environments
- Quick metadata validation without DataONE infrastructure

## Features

✅ **No Network Required** - All checks run locally  
✅ **Python Only** - No R dependencies needed  
✅ **Fast Execution** - No external API calls  
✅ **FAIR-Aligned** - Covers Findable, Accessible, and Reusable principles  

## Suite Contents

The suite includes **5 quality checks**:

### Findable (F)

| Check ID | Name | Description |
|----------|------|-------------|
| `resource.title.present` | Resource Title Present | Validates dataset has a meaningful title (≥5 chars) |
| `resource.abstract.present` | Resource Abstract Present | Validates dataset has a descriptive abstract (≥20 chars) |
| `resource.creator.present` | Resource Creator Present | Ensures at least one creator/author is specified |

### Accessible (A)

| Check ID | Name | Description |
|----------|------|-------------|
| `entity.attributeName.differs-2.0.0` | Entity Attribute Names Differ | Checks that attribute definitions aren't just the attribute name |

### Reusable (R)

| Check ID | Name | Description |
|----------|------|-------------|
| `resource.license.present-2.0.0` | Resource License Present | Verifies a license or usage terms are specified |

## Usage

### Command Line

```bash
# Basic usage
./.venv/bin/python -m metadig.metadigclient \\
  -runsuite \\
  -suitepath tests/testdata/metadata-offline-suite.xml \\
  -checkfolder tests/testdata/checks \\
  -mdoc path/to/metadata.xml \\
  -sysmeta path/to/sysmeta.xml \\
  -sp /tmp/test_hashstore

# Suppress warnings
./.venv/bin/python -m metadig.metadigclient \\
  -runsuite \\
  -suitepath tests/testdata/metadata-offline-suite.xml \\
  -checkfolder tests/testdata/checks \\
  -mdoc path/to/metadata.xml \\
  -sysmeta path/to/sysmeta.xml \\
  -sp /tmp/test_hashstore 2>&1 | grep -v "RuntimeWarning"
```

### Python API

```python
from metadig import suites
import json

# Run the suite
results_json = suites.run_suite(
    suite_path="tests/testdata/metadata-offline-suite.xml",
    checks_path="tests/testdata/checks",
    metadata_xml_path="path/to/metadata.xml",
    metadata_sysmeta_path="path/to/sysmeta.xml",
    store_props=None  # Not needed for metadata-only checks
)

# Parse results
results = json.loads(results_json)
print(f"Score: {results['run_status']}")
for check in results['results']:
    print(f"{check['status']}: {check['check_id']}")
```

## Example Output

```json
{
    "suite": "metadata-offline-suite.xml",
    "timestamp": "2025-10-24 20:31:22",
    "object_identifier": "doi:10.18739/A2RJ48X0F",
    "run_status": "SUCCESS",
    "results": [
        {
            "check_id": "resource.title.present.xml",
            "status": "SUCCESS",
            "output": "Dataset title found: 'Phytoplankton pigments...' (134 characters)"
        },
        {
            "check_id": "resource.abstract.present.xml",
            "status": "SUCCESS",
            "output": "Dataset abstract found: '...' (1532 characters, 213 words)"
        },
        {
            "check_id": "resource.creator.present.xml",
            "status": "SUCCESS",
            "output": "2 creators found: Gaffey, Oregon State University"
        },
        {
            "check_id": "entity.attributeName.differs-2.0.0.xml",
            "status": "FAILURE",
            "output": "This 1 attribute has a name different than definition: Notes"
        },
        {
            "check_id": "resource.license.present-2.0.0.xml",
            "status": "SUCCESS",
            "output": "The resource license 'This work is dedicated...' was found."
        }
    ]
}
```

## Supported Metadata Formats

The checks support multiple metadata standards through XPath dialects:

- **EML** (Ecological Metadata Language) 2.1, 2.2
- **DataCite** 4.x
- **ISO 19115** / ISO 19139 (Geographic metadata)

## Requirements

- Python 3.8+
- metadig-py library
- lxml
- No network access required!

## Integration with Dataverse

To test Dataverse datasets:

1. Export metadata as EML from Dataverse
2. Generate a sysmeta stub
3. Run the offline suite

```bash
# 1. Export EML
python scripts/dataverse_to_metadig.py \\
  --base-url https://dataverse.grit.ucsb.edu \\
  --persistent-id doi:10.5072/FK2/XXXXX \\
  --metadata-out /tmp/metadata.xml \\
  --sysmeta-out /tmp/sysmeta.xml

# 2. Run offline suite
./.venv/bin/python -m metadig.metadigclient \\
  -runsuite \\
  -suitepath tests/testdata/metadata-offline-suite.xml \\
  -checkfolder tests/testdata/checks \\
  -mdoc /tmp/metadata.xml \\
  -sysmeta /tmp/sysmeta.xml \\
  -sp /tmp/test_hashstore
```

## Custom Checks

You can add your own checks to the suite by:

1. Creating a new check XML file in `tests/testdata/checks/`
2. Adding the check ID to `metadata-offline-suite.xml`
3. Ensuring the check uses Python (not R) and doesn't make network calls

Example check template:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdq:check xmlns:mdq="https://nceas.ucsb.edu/mdqe/v1">
  <id>my.custom.check</id>
  <name>My Custom Check</name>
  <description>Description of what this checks</description>
  <type>Findable</type>
  <level>REQUIRED</level>
  <environment>python</environment>
  <code><![CDATA[
def call():
  global output
  global status
  global myVariable
  
  # Your validation logic here
  if myVariable:
    output = "Check passed"
    status = "SUCCESS"
    return True
  else:
    output = "Check failed"
    status = "FAILURE"
    return False
  ]]></code>
  <selector>
    <name>myVariable</name>
    <xpath>/eml/dataset/myElement//text()</xpath>
  </selector>
  <dialect>
    <name>Ecological Metadata Language</name>
    <xpath>boolean(/*[local-name() = 'eml'])</xpath>
  </dialect>
</mdq:check>
```

## Troubleshooting

### Issue: "RuntimeWarning: 'metadig.metadigclient' found in sys.modules"

**Solution**: This is harmless. Filter it out with:
```bash
command 2>&1 | grep -v "RuntimeWarning"
```

### Issue: "FileNotFoundError: 'hashstore.yaml' not found"

**Solution**: Copy the hashstore config:
```bash
mkdir -p /tmp/test_hashstore
cp hashstore/hashstore.yaml /tmp/test_hashstore/
```

### Issue: Checks still failing with network errors

**Solution**: Make sure you're using the latest version of `metadig/checks.py` that wraps `get_data_pids()` in a try-except block.

## Performance

Typical execution time: **< 2 seconds** for 5 checks

## License

Same as metadig-py (Apache 2.0)

## Related Resources

- [MetaDIG Project](https://github.com/NCEAS/metadig-py)
- [FAIR Principles](https://www.go-fair.org/fair-principles/)
- [EML Specification](https://eml.ecoinformatics.org/)
