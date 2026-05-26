#!/usr/bin/env python3
"""
Create minimal EML from Dataverse JSON metadata.
"""

import json
import sys
import urllib.request
import urllib.error
import ssl
from xml.sax.saxutils import escape
import dotenv

dotenv.load_dotenv()

DATAVERSE_API_TOKEN = dotenv.get_key(".env", "API_KEY")

def fetch_dataset_json(base_url, persistent_id, insecure=False, api_key=DATAVERSE_API_TOKEN):
    """Fetch dataset JSON from Dataverse API."""
    url = f"{base_url.rstrip('/')}/api/datasets/:persistentId?persistentId={persistent_id}"
    req = urllib.request.Request(url)
    context = ssl._create_unverified_context() if insecure else None
    if api_key:
        req.add_header('X-Dataverse-key', api_key)
    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"Error fetching dataset JSON: {e}")
        sys.exit(1)

def json_to_minimal_eml(dataset_json, output_path):
    """Convert Dataverse JSON to minimal EML."""
    data = dataset_json['data']
    latest = data['latestVersion']
    citation = latest['metadataBlocks']['citation']['fields']
    
    # Extract fields
    field_dict = {f['typeName']: f for f in citation}
    
    title = field_dict.get('title', {}).get('value', 'Unknown Title')
    
    # Get authors
    authors = field_dict.get('author', {}).get('value', [])
    
    # Get abstract
    descriptions = field_dict.get('dsDescription', {}).get('value', [])
    abstract = descriptions[0]['dsDescriptionValue']['value'] if descriptions else 'No description'
    
    # Get keywords
    keywords = field_dict.get('keyword', {}).get('value', [])
    
    # Get contacts
    contacts = field_dict.get('datasetContact', {}).get('value', [])
    
    # Get license
    license_info = latest.get('license', {})
    license_name = license_info.get('name', 'Unknown')
    license_uri = license_info.get('uri', '')
    
    # Get PID
    pid = f"{data['protocol']}:{data['authority']}/{data['identifier']}"
    
    # Build minimal EML
    eml = f'''<?xml version="1.0" encoding="UTF-8"?>
<eml:eml xmlns:eml="https://eml.ecoinformatics.org/eml-2.2.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xmlns:stmml="http://www.xml-cml.org/schema/stmml-1.2"
         xsi:schemaLocation="https://eml.ecoinformatics.org/eml-2.2.0 https://eml.ecoinformatics.org/eml-2.2.0/eml.xsd"
         system="https://dataverse.grit.ucsb.edu"
         scope="system">
    <dataset>
        <alternateIdentifier system="DOI">{escape(pid)}</alternateIdentifier>
        <title>{escape(title)}</title>
'''
    
    # Add creators
    for author in authors:
        author_name = author.get('authorName', {}).get('value', 'Unknown')
        eml += f'''        <creator>
            <individualName>
                <surName>{escape(author_name)}</surName>
            </individualName>
        </creator>
'''
    
    # Add contacts
    if contacts:
        for contact in contacts:
            contact_name = contact.get('datasetContactName', {}).get('value', 'Unknown')
            contact_email = contact.get('datasetContactEmail', {}).get('value', '')
            eml += f'''        <contact>
            <individualName>
                <surName>{escape(contact_name)}</surName>
            </individualName>
'''
            if contact_email:
                eml += f'''            <electronicMailAddress>{escape(contact_email)}</electronicMailAddress>
'''
            eml += '''        </contact>
'''
    else:
        eml += '''        <contact>
            <individualName>
                <surName>Unknown</surName>
            </individualName>
        </contact>
'''
    
    # Add publication date
    pub_date = data.get('publicationDate', '2025')
    eml += f'''        <pubDate>{escape(pub_date)}</pubDate>
'''
    
    # Add abstract
    eml += f'''        <abstract>
            <para>{escape(abstract)}</para>
        </abstract>
'''
    
    # Add keywords
    if keywords:
        eml += '''        <keywordSet>
'''
        for kw in keywords:
            kw_value = kw.get('keywordValue', {}).get('value', '')
            if kw_value:
                eml += f'''            <keyword>{escape(kw_value)}</keyword>
'''
        eml += '''        </keywordSet>
'''
    
    # Add license as intellectualRights
    eml += f'''        <intellectualRights>
            <para>License: {escape(license_name)}</para>
'''
    if license_uri:
        eml += f'''            <para>URI: {escape(license_uri)}</para>
'''
    eml += '''        </intellectualRights>
    </dataset>
</eml:eml>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(eml)
    
    return pid

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Create minimal EML from Dataverse JSON')
    parser.add_argument('--base-url', required=True, help='Dataverse base URL')
    parser.add_argument('--persistent-id', required=True, help='Dataset DOI')
    parser.add_argument('--output', required=True, help='Output EML file path')
    parser.add_argument('--insecure', action='store_true', help='Disable SSL verification')
    
    args = parser.parse_args()
    
    print(f"Fetching dataset metadata from Dataverse...")
    dataset_json = fetch_dataset_json(args.base_url, args.persistent_id, args.insecure)
    
    print(f"Converting to EML...")
    pid = json_to_minimal_eml(dataset_json, args.output)
    
    print(f"- EML created: {args.output}")
    print(f"- Dataset: {pid}")
