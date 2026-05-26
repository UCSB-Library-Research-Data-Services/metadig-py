# MetaDIG-py for Dataverse

This repository contains the MetaDIG quality assessment system adapted for UCSB Dataverse integration.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Available Checks](#available-checks)
- [Supported Metadata Formats](#supported-metadata-formats)
- [Key Features](#key-features)
- [Expanding the System](#expanding-the-system)
  - [Adding New Checks](#adding-new-checks)
  - [Creating Custom Suites](#creating-custom-suites)
  - [Leveraging Existing Check Libraries](#leveraging-existing-check-libraries)
  - [Advanced Customization](#advanced-customization)
  - [Best Practices](#best-practices)
  - [Integration Scenarios](#integration-scenarios)
- [Example Output](#example-output)
- [Testing Results](#testing-results)
- [Documentation](#documentation)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)

## Overview

MetaDIG (Metadata Assessment and Guidance) is a framework for assessing metadata quality against established standards. This setup enables:

- **Offline metadata validation** - No DataONE infrastructure required
- **Dataverse integration** - Direct API access to UCSB Dataverse datasets
- **FAIR compliance checking** - Validates Findable, Accessible, Interoperable, Reusable principles
- **Automated quality assessment** - Consistent, reproducible metadata evaluation

## How It Works

MetaDIG-py validates metadata quality through a modular architecture:

### Core Components

1. **Checks** - Individual quality tests defined as XML files
   - Each check contains XPath selectors to extract metadata values
   - Embedded Python or R code evaluates the extracted data
   - Returns SUCCESS, FAILURE, or ERROR status with explanatory output

2. **Suites** - Collections of related checks organized by standards
   - Group checks by FAIR principles, domain standards, or custom criteria
   - Define which checks run together and in what order
   - Support for metadata-only (offline) or full repository (online) modes

3. **Execution Engine** - Orchestrates check/suite execution
   - Loads metadata documents (EML, DataCite, ISO)
   - Runs XPath queries against the XML
   - Executes validation code in sandboxed environment
   - Aggregates results into structured JSON output

### Workflow for Dataverse Integration

```
Dataverse API → JSON Metadata → EML Conversion → MetaDIG Checks → Quality Report
```

**Step 1: Fetch Metadata**
- Query Dataverse API for dataset metadata
- Retrieve citation metadata, file information, keywords, etc.

**Step 2: Convert to Standard Format**
- Transform Dataverse JSON into EML 2.2.0 XML
- Map fields (title → `<title>`, author → `<creator>`, etc.)
- Generate valid XML that MetaDIG checks can parse

**Step 3: Generate System Metadata**
- Create DataONE-compatible system metadata stub
- Include identifier, format ID, member node, rights holder
- Required for suite execution framework

**Step 4: Execute Quality Checks**
- Load suite definition (XML file listing checks)
- Run each check against the EML metadata
- Collect pass/fail status and diagnostic messages

**Step 5: Generate Report**
- Aggregate all check results
- Calculate FAIR scores by category
- Output structured JSON with actionable feedback

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install lxml pandas chardet requests
pip install -e . --no-deps

# Setup hashstore (required for suite execution)
mkdir -p hashstore
cp hashstore/hashstore.yaml hashstore/
```

### 2. Validate Any Dataset (One Command!)

```bash
# Simple validation script - just provide the DOI
./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/YOUR_DOI

# Examples:
./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/AM1BXB
./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/5DVVVD
```

### 3. Manual Step-by-Step (Optional)

```bash
# If you want to run steps individually:

# Step 1: Convert Dataverse JSON to EML
python scripts/json_to_eml.py \
  --base-url https://dataverse.grit.ucsb.edu \
  --persistent-id doi:10.5072/FK2/AM1BXB \
  --output dataset.xml \
  --insecure

# Step 2: Generate system metadata stub
python -c "
import sys; sys.path.insert(0, 'scripts')
from dataverse_to_metadig import write_sysmeta_stub
write_sysmeta_stub(
    identifier='doi:10.5072/FK2/AM1BXB',
    authoritative_member_node='urn:node:DATAVERSE',
    rights_holder='public',
    file_name='dataset.xml',
    out_path='dataset_sysmeta.xml',
    format_id='https://eml.ecoinformatics.org/eml-2.2.0'
)
"

# Step 3: Run quality checks
python -m metadig.metadigclient \
  -runsuite \
  -suitepath tests/testdata/metadata-offline-suite.xml \
  -checkfolder tests/testdata/checks \
  -mdoc dataset.xml \
  -sysmeta dataset_sysmeta.xml \
  -sp ./hashstore
```

## Repository Structure

```
metadig-py/
├── metadig/                    # Core library
│   ├── checks.py              # Check execution engine
│   ├── suites.py              # Suite orchestration
│   ├── metadigclient.py       # Command-line interface
│   └── object_store.py        # Storage abstraction (incl. DataverseStore)
│
├── scripts/                    # Dataverse integration tools
│   ├── json_to_eml.py         # Convert Dataverse JSON → EML
│   └── dataverse_to_metadig.py # Sysmeta generation + EML export
│
├── tests/testdata/             # Check definitions and test data
│   ├── metadata-offline-suite.xml    # Offline quality suite
│   ├── checks/                       # Individual check definitions
│   │   ├── resource.title.present.xml
│   │   ├── resource.abstract.present.xml
│   │   ├── resource.creator.present.xml
│   │   ├── entity.attributeName.differs-2.0.0.xml
│   │   └── resource.license.present-2.0.0.xml
│   └── *.xml                         # Test EML documents
│
├── docs/                       # Documentation
│   ├── offline-suite-guide.md       # Comprehensive suite guide
│   ├── quick-test-guide.md          # Quick reference
│   └── dataverse-getting-started.md # Dataverse integration
│
└── hashstore/                  # HashStore configuration
    └── hashstore.yaml
```

## Available Checks

The offline metadata suite includes 5 quality checks:

| Check ID | FAIR | Description |
|----------|------|-------------|
| `resource.title.present` | F | Dataset has meaningful title (≥5 chars) |
| `resource.abstract.present` | F | Dataset has descriptive abstract (≥20 chars) |
| `resource.creator.present` | F | At least one creator/author specified |
| `entity.attributeName.differs` | A | Attribute definitions aren't just names |
| `resource.license.present` | R | License/usage terms specified |

## Supported Metadata Formats

- **EML** (Ecological Metadata Language) 2.1, 2.2
- **DataCite** 4.x
- **ISO 19115/19139** (Geographic metadata)

## Key Features

### 1. Offline Operation
- No network dependencies during check execution
- Perfect for CI/CD pipelines
- Fast execution (~2-3 seconds per suite)

### 2. Dataverse Integration
- Fetches metadata via Dataverse API
- Converts JSON to EML when native export unavailable
- Supports both public and restricted datasets (with API key)

### 3. FAIR Compliance
- Validates metadata against FAIR principles
- Provides actionable feedback
- Scores by category (Findable, Accessible, Reusable)

### 4. Extensible
- Add custom checks as XML files
- Create domain-specific suites
- Python and R check environments supported

## Expanding the System

The MetaDIG framework is designed to be highly extensible. You can customize and enhance it in several ways:

### Adding New Checks

Create custom quality checks for your specific requirements:

**1. Create a Check XML File**

Place in `tests/testdata/checks/your.custom.check.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdq:check xmlns:mdq="https://nceas.ucsb.edu/mdqe/v1">
    <id>your.custom.check.xml</id>
    <name>Your Custom Check</name>
    <description>Validates that your custom requirement is met</description>
    
    <!-- Environment: python or r -->
    <environment>python</environment>
    
    <!-- Select data from metadata using XPath -->
    <selector>
        <name>customField</name>
        <xpath>//eml:dataset/yourElement</xpath>
    </selector>
    
    <!-- Validation code -->
    <code><![CDATA[
def call():
    global output, status, customField
    
    # customField is extracted by the XPath selector above
    if customField and len(customField) > 0:
        output = f"Custom field found: {customField[0]}"
        status = "SUCCESS"
    else:
        output = "Custom field is missing"
        status = "FAILURE"
    
    return True
    ]]></code>
    
    <!-- FAIR category -->
    <type>Findable</type>
    <level>REQUIRED</level>
</mdq:check>
```

**2. Test the Check**

```bash
python -m metadig.metadigclient \
  -runcheck \
  -cxml tests/testdata/checks/your.custom.check.xml \
  -mdoc dataset.xml \
  -sysmeta dataset_sysmeta.xml \
  -sp ./hashstore
```

**Common Check Patterns:**

- **Presence checks**: Verify required fields exist
- **Format checks**: Validate field formats (dates, URLs, emails)
- **Completeness checks**: Ensure minimum content length/quality
- **Consistency checks**: Cross-validate related fields
- **Vocabulary checks**: Verify controlled vocabulary usage

### Creating Custom Suites

Organize checks into themed suites for different validation scenarios:

**1. Create a Suite XML File**

Place in `tests/testdata/your-custom-suite.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdq:suite xmlns:mdq="https://nceas.ucsb.edu/mdqe/v1">
    <id>your-custom-suite</id>
    <name>Your Custom Quality Suite</name>
    <description>Custom checks for your domain requirements</description>
    
    <!-- List all checks to include -->
    <check>
        <id>resource.title.present.xml</id>
        <level>REQUIRED</level>
    </check>
    
    <check>
        <id>resource.abstract.present.xml</id>
        <level>REQUIRED</level>
    </check>
    
    <check>
        <id>your.custom.check.xml</id>
        <level>OPTIONAL</level>
    </check>
    
    <!-- Add more checks as needed -->
</mdq:suite>
```

**2. Run the Custom Suite**

```bash
python -m metadig.metadigclient \
  -runsuite \
  -suitepath tests/testdata/your-custom-suite.xml \
  -checkfolder tests/testdata/checks \
  -mdoc dataset.xml \
  -sysmeta dataset_sysmeta.xml \
  -sp ./hashstore
```

### Suite Examples by Use Case

**Minimal Compliance Suite** (Quick validation)
```xml
- resource.title.present
- resource.creator.present
- resource.license.present
```

**Data Quality Suite** (For tabular data)
```xml
- entity.attributeName.differs
- entity.attributeDefinition.present
- entity.attributeUnit.present
- data.table.columnNames.unique
- data.table.rows.validated
```

**Geospatial Suite** (For spatial datasets)
```xml
- resource.geographicCoverage.present
- resource.boundingBox.valid
- resource.coordinateSystem.present
- resource.spatialResolution.present
```

**Temporal Suite** (For time-series data)
```xml
- resource.temporalCoverage.present
- resource.temporalCoverage.rangeValid
- entity.datetime.format.valid
- entity.datetime.timezone.present
```

**Domain-Specific Suite** (e.g., Marine Biology)
```xml
- resource.taxonomicCoverage.present
- resource.samplingProtocol.present
- resource.qualityControl.present
- resource.funding.present
```

### Leveraging Existing Check Libraries

MetaDIG has extensive check libraries you can incorporate:

**1. Browse Available Checks**

Visit the [metadig-checks repository](https://github.com/NCEAS/metadig-checks):
- 200+ pre-built quality checks
- Organized by metadata standards (EML, ISO, DataCite)
- Covers all FAIR principles
- Includes R and Python implementations

**2. Copy Checks to Your Project**

```bash
# Download specific checks
wget https://raw.githubusercontent.com/NCEAS/metadig-checks/main/src/checks/resource.contactEmail.present.xml \
  -O tests/testdata/checks/resource.contactEmail.present.xml

# Or clone the entire repository
git clone https://github.com/NCEAS/metadig-checks.git
cp metadig-checks/src/checks/*.xml tests/testdata/checks/
```

**3. Use in Your Suites**

Just reference the check ID in your suite XML.

### Advanced Customization

**Multi-format Support**

Add XPath selectors for different metadata standards:

```xml
<!-- EML selector -->
<selector>
    <name>emlTitle</name>
    <xpath>//eml:dataset/title</xpath>
</selector>

<!-- DataCite selector -->
<selector>
    <name>dataciteTitle</name>
    <xpath>//datacite:title</xpath>
</selector>

<!-- ISO 19115 selector -->
<selector>
    <name>isoTitle</name>
    <xpath>//gmd:identificationInfo//gmd:title/gco:CharacterString</xpath>
</selector>
```

**Complex Validation Logic**

Use Python libraries for sophisticated checks:

```python
def call():
    import re
    from urllib.parse import urlparse
    
    global output, status, url_field
    
    # Validate URL format
    try:
        result = urlparse(url_field[0])
        if all([result.scheme, result.netloc]):
            # Additional check: verify it's HTTPS
            if result.scheme == 'https':
                output = f"Valid HTTPS URL: {url_field[0]}"
                status = "SUCCESS"
            else:
                output = f"URL should use HTTPS: {url_field[0]}"
                status = "FAILURE"
        else:
            output = f"Invalid URL format: {url_field[0]}"
            status = "FAILURE"
    except Exception as e:
        output = f"Error validating URL: {str(e)}"
        status = "ERROR"
    
    return True
```

**Scoring and Weighting**

Customize how checks contribute to overall scores:

```xml
<check>
    <id>resource.title.present.xml</id>
    <level>REQUIRED</level>  <!-- Must pass -->
</check>

<check>
    <id>resource.keywords.present.xml</id>
    <level>OPTIONAL</level>  <!-- Nice to have -->
</check>

<check>
    <id>resource.funding.present.xml</id>
    <level>INFO</level>  <!-- Informational only -->
</check>
```

### Best Practices

1. **Start Small**: Begin with the offline metadata suite, then add checks incrementally
2. **Test Thoroughly**: Validate new checks against diverse real-world datasets
3. **Document Clearly**: Explain what each check does and why it matters
4. **Organize by Theme**: Group related checks into suites (FAIR, domain, quality level)
5. **Reuse Existing Checks**: Browse metadig-checks before writing custom ones
6. **Version Control**: Track changes to your checks and suites in git
7. **Provide Feedback**: Make failure messages actionable ("Add keyword X" vs "Keywords missing")

### Integration Scenarios

**CI/CD Pipeline**
```yaml
# .github/workflows/metadata-qa.yml
- name: Validate Metadata Quality
  run: |
    ./scripts/validate_dataverse_dataset.sh $DATASET_DOI
    # Parse JSON output and fail if checks don't pass
```

**Batch Processing**
```bash
# Validate all datasets in a collection
for doi in $(cat dataset_list.txt); do
  ./scripts/validate_dataverse_dataset.sh $doi > results/${doi//\//_}.json
done
```

**Custom Reporting**
```python
# Parse JSON results and generate HTML reports
import json
results = json.load(open('results.json'))
# Generate dashboard, charts, trends, etc.
```

## Example Output

```json
{
    "suite": "metadata-offline-suite.xml",
    "timestamp": "2025-10-24 20:35:12",
    "object_identifier": "doi:10.5072/FK2/AM1BXB",
    "run_status": "SUCCESS",
    "results": [
        {
            "check_id": "resource.title.present.xml",
            "status": "SUCCESS",
            "output": "Dataset title found (97 characters)"
        },
        {
            "check_id": "resource.abstract.present.xml",
            "status": "SUCCESS",
            "output": "Dataset abstract found (2220 characters, 314 words)"
        }
        // ... more checks
    ]
}
```

## Testing Results

Tested with UCSB Dataverse datasets:
- ✅ **doi:10.5072/FK2/AM1BXB** - Marine debris baseline (5/5 checks passed)
- ✅ **doi:10.5072/FK2/5DVVVD** - Chinook habitat restoration (5/5 checks passed)

**Success rate:** 100% (10/10 checks passed across all datasets)

## Documentation

- **[README_DATAVERSE.md](README_DATAVERSE.md)** (this file) - Complete guide including:
  - How MetaDIG works (architecture and workflow)
  - Expanding with custom checks and suites
  - Integration scenarios and best practices
- **[How Validation Works](docs/how-validation-works.md)** - ⭐ **Deep dive explaining how checks execute step-by-step with real examples**
- **[Offline Suite Guide](docs/offline-suite-guide.md)** - Detailed suite documentation
- **[Quick Test Guide](docs/quick-test-guide.md)** - Step-by-step testing instructions
- **[Dataverse Integration](docs/dataverse-getting-started.md)** - Dataverse setup guide

## Additional Resources

- **[MetaDIG Checks Repository](https://github.com/NCEAS/metadig-checks)** - 200+ pre-built quality checks
- **[MetaDIG Engine](https://github.com/NCEAS/metadig-engine)** - Java-based MetaDIG engine
- **[FAIR Principles](https://www.go-fair.org/fair-principles/)** - Findable, Accessible, Interoperable, Reusable
- **[EML Specification](https://eml.ecoinformatics.org/)** - Ecological Metadata Language standard

## Requirements

- Python 3.8+
- Dependencies: `lxml`, `pandas`, `chardet`, `requests`
- Network access for initial metadata fetch only

## Troubleshooting

### SSL Certificate Errors
Use `--insecure` flag for testing (not recommended for production):
```bash
python scripts/json_to_eml.py --insecure ...
```

### RuntimeWarning Messages
Filter them out in terminal output:
```bash
command 2>&1 | grep -v "RuntimeWarning"
```

### HashStore Not Found
Copy the configuration:
```bash
mkdir -p /tmp/test_hashstore
cp hashstore/hashstore.yaml /tmp/test_hashstore/
```

## License

Apache 2.0 - See LICENSE file

## Summary: Getting Started Checklist

Ready to start validating your Dataverse metadata? Follow this checklist:

- [ ] **Setup** - Install dependencies and configure environment
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install lxml pandas chardet requests
  pip install -e . --no-deps
  ```

- [ ] **Test** - Validate your first dataset
  ```bash
  ./scripts/validate_dataverse_dataset.sh doi:YOUR_DOI_HERE
  ```

- [ ] **Customize** - Add checks specific to your needs
  - Browse [metadig-checks](https://github.com/NCEAS/metadig-checks) for 200+ existing checks
  - Create custom checks in `tests/testdata/checks/`
  - Build domain-specific suites in `tests/testdata/`

- [ ] **Integrate** - Incorporate into your workflow
  - Add to CI/CD pipelines for automated validation
  - Batch process datasets for repository-wide quality reports
  - Generate custom reports from JSON results

- [ ] **Expand** - Enhance based on your domain
  - Add geospatial checks for spatial data
  - Add temporal checks for time-series data
  - Add domain-specific vocabulary validation

**Questions?** Check the [documentation](#documentation) or refer to the detailed guides in the `docs/` folder.

## Credits

- **MetaDIG Project** - [NCEAS](https://github.com/NCEAS/metadig-py)
- **Dataverse Integration** - UCSB Library / Bren School collaboration
- **FAIR Principles** - [GO FAIR](https://www.go-fair.org/)

## Related Projects

- [metadig-engine](https://github.com/NCEAS/metadig-engine) - Java-based MetaDIG engine
- [metadig-checks](https://github.com/NCEAS/metadig-checks) - Check library repository
- [Dataverse Project](https://dataverse.org/) - Open source research data repository
