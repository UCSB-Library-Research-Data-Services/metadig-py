# How MetaDIG Validates Metadata - Complete Walkthrough

This guide explains exactly how MetaDIG validation works under the hood, with real examples.

## The Complete Picture

When you run `./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/XXXXX`, here's the step-by-step flow:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: Fetch Metadata                           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
    Dataverse API returns JSON with dataset information:
    {
      "title": "Ocean Sediment Thickness",
      "author": "E. O. Straume",
      "description": "Total sediment thickness...",
      "keywords": ["oceanography", "sediments"],
      "license": "CC0 1.0"
    }

┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 2: Convert to EML XML                       │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
    JSON is transformed into EML 2.2.0 XML format:
    
    <eml>
      <dataset>
        <title>Ocean Sediment Thickness</title>
        <creator>
          <individualName>E. O. Straume</individualName>
        </creator>
        <abstract>Total sediment thickness...</abstract>
        <keywordSet>
          <keyword>oceanography</keyword>
          <keyword>sediments</keyword>
        </keywordSet>
        <licensed>
          <licenseName>CC0 1.0</licenseName>
        </licensed>
      </dataset>
    </eml>

┌─────────────────────────────────────────────────────────────────────┐
│               STEP 3: Generate System Metadata                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
    Create a stub file with administrative info:
    
    <systemMetadata>
      <identifier>doi:10.5072/FK2/XXXXX</identifier>
      <formatId>https://eml.ecoinformatics.org/eml-2.2.0</formatId>
      <authoritativeMemberNode>urn:node:DATAVERSE</authoritativeMemberNode>
      <rightsHolder>public</rightsHolder>
      <dateUploaded>2025-10-24T20:48:00Z</dateUploaded>
    </systemMetadata>

┌─────────────────────────────────────────────────────────────────────┐
│                STEP 4: Load Suite Definition                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
    Read metadata-offline-suite.xml which lists 5 checks to run:
    
    ├─ resource.title.present.xml           (Findable)
    ├─ resource.abstract.present.xml        (Findable)
    ├─ resource.creator.present.xml         (Findable)
    ├─ entity.attributeName.differs.xml     (Accessible)
    └─ resource.license.present.xml         (Reusable)

┌─────────────────────────────────────────────────────────────────────┐
│              STEP 5: Run Each Check (5 times)                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Deep Dive: How ONE Check Executes

For EACH check in the suite, here's the detailed process:

### Example: `resource.title.present.xml`

#### 5.1) Load Check Definition

The system parses `resource.title.present.xml` to understand three things:

**a) What to extract** - The `<selector>` with XPath:
```xml
<selector>
  <name>title</name>
  <xpath>/eml/dataset/title//text()[normalize-space()]</xpath>
</selector>
```

**b) How to validate** - The Python `<code>`:
```python
def call():
  global output, status, title
  
  if not title or len(title) < 5:
    status = "FAILURE"
    output = "Title missing or too short"
  else:
    status = "SUCCESS"
    output = f"Dataset title found: '{title}'"
```

**c) What standards it supports** - The `<dialect>`:
```xml
<dialect>
  <name>Ecological Metadata Language</name>
  <xpath>boolean(/*[local-name() = 'eml'])</xpath>
</dialect>
```

#### 5.2) Check If Valid For This Metadata

Test the dialect XPath against your metadata document:

```python
# Test: boolean(/*[local-name() = 'eml'])
# On your document: <eml>...</eml>
# Result: TRUE ✓ 
# → Check can proceed!
```

If this returned FALSE (e.g., you had DataCite metadata but the check only supports EML), the check would be skipped.

#### 5.3) Extract Data Using XPath (Selector)

Run the XPath query on your EML document:

```python
# XPath: /eml/dataset/title//text()[normalize-space()]
# Searches for: <eml><dataset><title>TEXT HERE</title>

# Your document has:
# <eml>
#   <dataset>
#     <title>Ocean Sediment Thickness</title>
#   </dataset>
# </eml>

# ✓ FOUND: "Ocean Sediment Thickness"
# → Store in Python variable called "title"
```

The XPath finds all text inside `<title>` elements, normalizes whitespace, and returns it as a list:
```python
title = ["Ocean Sediment Thickness"]
```

#### 5.4) Execute Validation Code (Python)

Now run the Python code from the check, with `title` already populated:

```python
def call():
  global output, status, title
  
  # title = ["Ocean Sediment Thickness"] (extracted above)
  
  # Check if title exists
  if 'title' not in globals() or title is None:
    output = "A dataset title was not found."
    status = "FAILURE"
    return False
  
  # Check if blank
  title_str = str(title[0]) if isinstance(title, list) else str(title)
  if title_str.strip() == "":
    output = "The dataset title is blank."
    status = "FAILURE"
    return False
  
  # Check minimum length
  if len(title_str) < 5:
    output = f"Title too short ({len(title_str)} chars)"
    status = "FAILURE"
    return False
  
  # Success!
  output = f"Dataset title found: '{title_str}' ({len(title_str)} chars)"
  status = "SUCCESS"
  return True

# Execution result:
# status = "SUCCESS"
# output = "Dataset title found: 'Ocean Sediment Thickness' (26 chars)"
```

#### 5.5) Store Result

Save the check result to the results array:

```json
{
  "check_id": "resource.title.present.xml",
  "status": "SUCCESS",
  "output": "Dataset title found: 'Ocean Sediment Thickness' (26 chars)",
  "identifiers": ["N/A"]
}
```

## Complete Real-World Example

Let's trace `resource.abstract.present.xml` from start to finish:

### Input: Your EML Metadata

```xml
<eml>
  <dataset>
    <abstract>
      <para>The Total Sediment Thickness database for the World's 
      Oceans and Marginal Seas is a compilation of sediment thickness 
      measurements obtained from geophysical surveys...</para>
    </abstract>
  </dataset>
</eml>
```

### Step 1: Dialect Check

```xml
<dialect>
  <xpath>boolean(/*[local-name() = 'eml'])</xpath>
</dialect>
```

```python
# Test: Is this EML metadata?
# Your doc starts with <eml>
# Result: TRUE ✓ 
```

### Step 2: Extract Data (Selector)

```xml
<selector>
  <name>abstract</name>
  <xpath>/eml/dataset/abstract//text()[normalize-space()]</xpath>
</selector>
```

```python
# XPath searches for text inside <abstract>
# Found: "The Total Sediment Thickness database for the World's 
#         Oceans and Marginal Seas is a compilation of..."
# Length: 750 characters

abstract = ["The Total Sediment Thickness database for the World's Oceans..."]
```

### Step 3: Execute Python Validation

```python
def call():
  global output, status, abstract
  
  # abstract = ["The Total Sediment Thickness database..."] (from XPath)
  
  abstract_text = abstract[0] if abstract else ""
  
  # Check if exists and has minimum content
  if not abstract_text or len(abstract_text) < 20:
    status = "FAILURE"
    output = "Abstract missing or too short"
    return False
  
  # Calculate metrics
  word_count = len(abstract_text.split())
  char_count = len(abstract_text)
  
  # Success!
  status = "SUCCESS"
  output = f"Dataset abstract found ({char_count} chars, {word_count} words)"
  return True

# Result:
# abstract_text = 750 characters, 108 words
# status = "SUCCESS"
# output = "Dataset abstract found (750 characters, 108 words)"
```

### Step 4: Return Result

```json
{
  "check_id": "resource.abstract.present.xml",
  "status": "SUCCESS",
  "output": "Dataset abstract found (750 characters, 108 words)",
  "identifiers": ["N/A"]
}
```

## Final Report: Aggregating All Results

After all 5 checks complete, the results are combined:

```json
{
  "suite": "metadata-offline-suite.xml",
  "timestamp": "2025-10-24 20:48:05",
  "object_identifier": "doi:10.5072/FK2/SQNCB7",
  "run_status": "SUCCESS",
  "run_comments": [],
  "sysmeta": {
    "origin_member_node": "urn:node:DATAVERSE",
    "rights_holder": "public",
    "date_uploaded": "2025-10-25T03:47:18.586389+00:00",
    "format_id": "https://eml.ecoinformatics.org/eml-2.2.0",
    "obsoletes": null
  },
  "results": [
    {
      "check_id": "resource.title.present.xml",
      "status": "SUCCESS",
      "output": "Dataset title found: 'Ocean Total Sediment...' (63 chars)"
    },
    {
      "check_id": "resource.abstract.present.xml",
      "status": "SUCCESS",
      "output": "Dataset abstract found (750 characters, 108 words)"
    },
    {
      "check_id": "resource.creator.present.xml",
      "status": "SUCCESS",
      "output": "1 creator found: E. O. Straume"
    },
    {
      "check_id": "entity.attributeName.differs-2.0.0.xml",
      "status": "SUCCESS",
      "output": "All 0 attributes have definitions that differ from the name"
    },
    {
      "check_id": "resource.license.present-2.0.0.xml",
      "status": "SUCCESS",
      "output": "The resource license 'License: CC0 1.0' was found."
    }
  ]
}
```

## Key Concepts Explained

### 1. XPath (Selectors)

XPath is a query language for XML documents - like SQL for databases but for XML trees.

**Examples:**
- `/eml/dataset/title` → Find `<title>` inside `<dataset>` inside `<eml>`
- `//creator` → Find any `<creator>` element anywhere in the document
- `//text()[normalize-space()]` → Get all text nodes, excluding blank ones

**Why it's powerful:**
- Handles complex nested structures
- Works across different metadata standards
- Extracts exactly what you need

### 2. Dialect (Compatibility Check)

Different metadata standards use different XML structures:
- **EML**: `<eml><dataset><title>`
- **DataCite**: `<resource><titles><title>`
- **ISO 19115**: `<MD_Metadata><identificationInfo><citation><title>`

Each check defines which standards it supports using dialect XPaths. Before running, MetaDIG verifies your metadata matches.

### 3. Python Code (Validation Logic)

The actual business rules that check quality:
- Receives extracted data as Python variables (e.g., `title`, `abstract`)
- Performs validation (length checks, format validation, presence tests)
- Sets `status` ("SUCCESS", "FAILURE", or "ERROR")
- Sets `output` (human-readable message explaining the result)

### 4. Global Variables (The Bridge)

Python's `global` keyword connects XPath extraction to validation:

```python
def call():
  global output, status, title  # These are the bridge!
  
  # 'title' was populated by XPath selector
  # 'status' and 'output' are set by this code
  
  if title:
    status = "SUCCESS"
    output = f"Found: {title}"
  else:
    status = "FAILURE"
    output = "Title not found"
```

## Code Files Involved

### `metadig/checks.py`

**Key function: `run_check()`**

This function:
1. Loads the check XML and metadata XML
2. Tests if check is valid for this metadata (dialect check)
3. Extracts data using XPath selectors
4. Executes the Python validation code
5. Returns the result as JSON

```python
def run_check(check_xml_path, metadata_xml_path, metadata_sysmeta_path, store_props):
    # Load metadata
    metadata_doc = etree.parse(metadata_xml_path).getroot()
    
    # Load check
    check_doc = etree.parse(check_xml_path).getroot()
    
    # Verify check is valid for this metadata
    if not is_check_valid(check_doc, metadata_doc):
        return
    
    # Extract data using selectors
    selectors = check_doc.xpath(".//selector")
    check_vars = {}
    for selector in selectors:
        selector_name = selector.xpath("name")[0].text
        variable_list = select_nodes(metadata_doc, selector)
        check_vars[selector_name] = variable_list  # e.g., check_vars["title"] = ["Ocean..."]
    
    # Execute Python code
    code = check_doc.xpath("code")[0].text
    exec(code + "\ncall()", check_vars)
    
    # Return result
    return json.dumps({
        "output": check_vars.get("output"),
        "status": check_vars.get("status")
    })
```

### `metadig/suites.py`

**Key function: `run_suite()`**

This function:
1. Loads the suite XML to get list of checks
2. Finds the check files for each check ID
3. Runs each check (calls `run_check()` for each)
4. Aggregates all results into a final report

```python
def run_suite(suite_path, checks_path, metadata_xml_path, metadata_sysmeta_path, store_props):
    # Load suite
    suite_doc = etree.parse(suite_path).getroot()
    
    # Get list of checks
    checks_to_run = []
    for check in suite_doc.findall("check"):
        check_id = check.find("id").text
        check_file = find_check_file(checks_path, check_id)
        checks_to_run.append(check_file)
    
    # Run each check
    results = []
    for check_file in checks_to_run:
        result = run_check(check_file, metadata_xml_path, metadata_sysmeta_path, store_props)
        results.append(result)
    
    # Return aggregated report
    return {
        "suite": suite_name,
        "timestamp": datetime.now(),
        "run_status": "SUCCESS" if all_passed else "FAILURE",
        "results": results
    }
```

## Why This Design Works

### ✓ Separation of Concerns
- **XPath**: "WHERE to look" (structure/location)
- **Python**: "WHAT to check" (business logic)
- **XML**: "HOW to configure" (declarative rules)

### ✓ Flexibility
- Add new checks without changing code
- Support multiple metadata standards (EML, DataCite, ISO)
- Custom validation rules per domain

### ✓ Reusability
- Same check works for different standards
- Just provide different XPath selectors
- Share checks across communities

### ✓ Extensibility
- Add new checks as XML files
- Group checks into themed suites
- No code compilation needed

## Creating Your Own Check

Now that you understand how it works, here's a template:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdq:check xmlns:mdq="https://nceas.ucsb.edu/mdqe/v1">
  <id>my.custom.check</id>
  <name>My Custom Check</name>
  <description>Validates something important</description>
  <environment>python</environment>
  
  <!-- Extract data -->
  <selector>
    <name>myField</name>
    <xpath>//your/xpath/here</xpath>
  </selector>
  
  <!-- Validate data -->
  <code><![CDATA[
def call():
  global output, status, myField
  
  if myField and len(myField) > 0:
    output = f"Found: {myField[0]}"
    status = "SUCCESS"
  else:
    output = "Field not found"
    status = "FAILURE"
  
  return True
  ]]></code>
  
  <!-- Specify compatibility -->
  <dialect>
    <name>Ecological Metadata Language</name>
    <xpath>boolean(/*[local-name() = 'eml'])</xpath>
  </dialect>
  
  <type>Findable</type>
  <level>REQUIRED</level>
</mdq:check>
```

## Summary

**The validation flow:**
1. **Fetch** metadata from Dataverse (JSON)
2. **Convert** JSON → EML XML
3. **Load** suite definition (which checks to run)
4. **For each check:**
   - Test if check applies (dialect)
   - Extract data (XPath selector)
   - Validate data (Python code)
   - Store result
5. **Aggregate** all results into JSON report

**The magic:**
- XPath extracts data into Python variables
- Python code validates and sets status/output
- No hardcoded logic - everything is configurable via XML files
- Works across different metadata standards

Now you understand how MetaDIG validates metadata! 🎉
