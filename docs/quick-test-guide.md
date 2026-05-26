# Quick Start: Testing Dataverse Datasets with MetaDIG

## Test Any Dataverse Dataset in 3 Steps

### Step 1: Convert Dataverse JSON to EML

```bash
./.venv/bin/python scripts/json_to_eml.py \
  --base-url https://dataverse.grit.ucsb.edu \
  --persistent-id doi:10.5072/FK2/YOUR_DATASET \
  --output /tmp/dataset.xml \
  --insecure
```

### Step 2: Generate System Metadata Stub

```bash
./.venv/bin/python -c "
import sys
sys.path.insert(0, '$(pwd)')
from scripts.dataverse_to_metadig import write_sysmeta_stub

write_sysmeta_stub(
    identifier='doi:10.5072/FK2/YOUR_DATASET',
    authoritative_member_node='urn:node:DATAVERSE_GRIT',
    rights_holder='CN=dataverse.grit.ucsb.edu,DC=dataone,DC=org',
    file_name='dataset.xml',
    out_path='/tmp/sysmeta.xml',
    format_id='https://eml.ecoinformatics.org/eml-2.2.0'
)
print('✓ Sysmeta created')
"
```

### Step 3: Run Quality Checks

```bash
./.venv/bin/python -m metadig.metadigclient \
  -runsuite \
  -suitepath tests/testdata/metadata-offline-suite.xml \
  -checkfolder tests/testdata/checks \
  -mdoc /tmp/dataset.xml \
  -sysmeta /tmp/sysmeta.xml \
  -sp /tmp/test_hashstore 2>&1 | grep -v "RuntimeWarning"
```

## One-Liner Script

Create a simple test script:

```bash
#!/bin/bash
DOI="$1"

echo "Testing dataset: $DOI"
echo "Step 1: Creating EML..."
./.venv/bin/python scripts/json_to_eml.py \
  --base-url https://dataverse.grit.ucsb.edu \
  --persistent-id "$DOI" \
  --output /tmp/dataset.xml \
  --insecure

echo "Step 2: Creating sysmeta..."
./.venv/bin/python -c "
import sys
sys.path.insert(0, '$(pwd)')
from scripts.dataverse_to_metadig import write_sysmeta_stub
write_sysmeta_stub(
    identifier='$DOI',
    authoritative_member_node='urn:node:DATAVERSE_GRIT',
    rights_holder='CN=dataverse.grit.ucsb.edu,DC=dataone,DC=org',
    file_name='dataset.xml',
    out_path='/tmp/sysmeta.xml',
    format_id='https://eml.ecoinformatics.org/eml-2.2.0'
)
"

echo "Step 3: Running quality checks..."
./.venv/bin/python -m metadig.metadigclient \
  -runsuite \
  -suitepath tests/testdata/metadata-offline-suite.xml \
  -checkfolder tests/testdata/checks \
  -mdoc /tmp/dataset.xml \
  -sysmeta /tmp/sysmeta.xml \
  -sp /tmp/test_hashstore 2>&1 | grep -v "RuntimeWarning" | jq .
```

Save as `test_dataset.sh` and use:
```bash
chmod +x test_dataset.sh
./test_dataset.sh doi:10.5072/FK2/AM1BXB
```

## Example: Tested Dataset

**Dataset:** Baseline Marine Debris Data (2015-2023) - Proposed Chumash Heritage National Marine Sanctuary  
**DOI:** doi:10.5072/FK2/AM1BXB  
**Result:** ✓✓✓✓✓ 5/5 checks passed (100%)

### Check Results:
- ✓ Title present and meaningful (97 characters)
- ✓ Abstract present and comprehensive (2220 characters, 314 words)
- ✓ Creators properly listed (5 authors)
- ✓ No attribute definition issues
- ✓ License clearly specified (CC0 1.0)

## Available Checks

The offline metadata suite includes:

| Check | FAIR Category | Purpose |
|-------|---------------|---------|
| resource.title.present | Findable | Validates title exists and is meaningful |
| resource.abstract.present | Findable | Validates description quality |
| resource.creator.present | Findable | Ensures authors are credited |
| entity.attributeName.differs | Accessible | Checks data documentation quality |
| resource.license.present | Reusable | Verifies usage terms |

## Tips

1. **Setup hashstore once:**
   ```bash
   mkdir -p /tmp/test_hashstore
   cp hashstore/hashstore.yaml /tmp/test_hashstore/
   ```

2. **Pretty print results with jq:**
   ```bash
   ... | jq '.results[] | {check: .check_id, status: .status, output: .output}'
   ```

3. **Test multiple datasets:**
   ```bash
   for doi in doi:10.5072/FK2/XXXXX doi:10.5072/FK2/YYYYY; do
       ./test_dataset.sh "$doi"
   done
   ```

## Troubleshooting

**Issue:** 403 Forbidden when accessing dataset  
**Solution:** Dataset may be restricted. Check access permissions or try a public dataset.

**Issue:** EML export not available  
**Solution:** Use `json_to_eml.py` script (already included in workflow above)

**Issue:** SSL certificate errors  
**Solution:** Use `--insecure` flag (for testing only)
