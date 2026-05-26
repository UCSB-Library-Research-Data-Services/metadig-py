#!/usr/bin/env python3
"""
Fetch metadata from a Dataverse dataset and prepare inputs for MetaDIG-py.

What it does:
- Downloads EML (or another export format) for a dataset via the Dataverse API
- Generates a minimal DataONE System Metadata (sysmeta) stub for the metadata object

This enables running metadata-only MetaDIG checks for Dataverse datasets, without
needing DataONE membership. Data checks will be skipped unless your dataset is
also available in DataONE.

Example:
  poetry run python scripts/dataverse_to_metadig.py \
    --base-url https://dataverse.grit.ucsb.edu \
    --persistent-id doi:10.5072/FK2/IRJI89 \
    --api-key $DATAVERSE_KEY \
    --metadata-out /tmp/dataset.xml \
    --sysmeta-out /tmp/sysmeta.xml \
    --authoritative-member-node urn:node:KNB

Then run:
  poetry run metadigpy -runcheck \
    -store_path=$(pwd)/hashstore \
    -check_xml=$(pwd)/tests/testdata/checks/resource.license.present-2.0.0.xml \
    -metadata_doc=/tmp/dataset.xml \
    -sysmeta_doc=/tmp/sysmeta.xml
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timezone


def http_get(url: str, headers: dict | None = None, timeout: int = 60, insecure: bool = False) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    context = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
        return resp.read()


def export_eml(base_url: str, persistent_id: str, api_key: str | None, out_path: str, insecure: bool = False) -> None:
    export_url = (
        f"{base_url.rstrip('/')}/api/datasets/export?"
        f"exporter=eml&persistentId={urllib.parse.quote(persistent_id)}"
    )
    headers = {"X-Dataverse-key": api_key} if api_key else {}
    data = http_get(export_url, headers=headers, insecure=insecure)
    with open(out_path, "wb") as f:
        f.write(data)


def fetch_dataset_json(base_url: str, persistent_id: str, api_key: str | None, insecure: bool = False) -> dict:
    url = (
        f"{base_url.rstrip('/')}/api/v1/datasets/:persistentId/?persistentId="
        f"{urllib.parse.quote(persistent_id)}"
    )
    headers = {"X-Dataverse-key": api_key} if api_key else {}
    raw = http_get(url, headers=headers, insecure=insecure)
    return json.loads(raw.decode("utf-8"))


def pick_rights_holder(dataset_json: dict, fallback: str | None) -> str:
    if fallback:
        return fallback
    try:
        latest = dataset_json["data"]["latestVersion"]
        # Prefer a contact name if available
        for field in latest.get("metadataBlocks", {}).get("citation", {}).get("fields", []):
            if field.get("typeName") == "datasetContact":
                vals = field.get("value", [])
                if vals and isinstance(vals, list):
                    contact = vals[0]
                    name = contact.get("datasetContactName", {}).get("value")
                    if name:
                        return name
        # Fallback to depositor
        for field in latest.get("metadataBlocks", {}).get("citation", {}).get("fields", []):
            if field.get("typeName") == "depositor":
                val = field.get("value")
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass
    return "public"


def write_sysmeta_stub(
    identifier: str,
    authoritative_member_node: str,
    rights_holder: str,
    file_name: str,
    out_path: str,
    format_id: str = "https://eml.ecoinformatics.org/eml-2.2.0",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns3:systemMetadata xmlns:ns2="http://ns.dataone.org/service/types/v1" xmlns:ns3="http://ns.dataone.org/service/types/v2.0">
    <serialVersion>1</serialVersion>
    <identifier>{identifier}</identifier>
    <formatId>{format_id}</formatId>
    <size>0</size>
    <checksum algorithm="MD5">00000000000000000000000000000000</checksum>
    <submitter>{rights_holder}</submitter>
    <rightsHolder>{rights_holder}</rightsHolder>
    <accessPolicy>
        <allow>
            <subject>public</subject>
            <permission>read</permission>
        </allow>
    </accessPolicy>
    <replicationPolicy replicationAllowed="false" numberReplicas="0"/>
    <archived>false</archived>
    <dateUploaded>{now}</dateUploaded>
    <dateSysMetadataModified>{now}</dateSysMetadataModified>
    <originMemberNode>{authoritative_member_node}</originMemberNode>
    <authoritativeMemberNode>{authoritative_member_node}</authoritativeMemberNode>
    <fileName>{file_name}</fileName>
</ns3:systemMetadata>
'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare MetaDIG-py inputs from Dataverse")
    parser.add_argument("--base-url", required=True, help="Dataverse base URL")
    parser.add_argument("--persistent-id", required=True, help="Dataset persistentId")
    parser.add_argument("--api-key", help="Dataverse API key for private/restricted datasets")
    parser.add_argument("--metadata-out", required=True, help="Path to write exported EML")
    parser.add_argument("--sysmeta-out", required=True, help="Path to write sysmeta stub XML")
    parser.add_argument(
        "--authoritative-member-node",
        default="urn:node:KNB",
        help="DataONE member node ID to embed in stub (default: urn:node:KNB)",
    )
    parser.add_argument("--rights-holder", help="Override rightsHolder; else inferred from dataset")
    parser.add_argument(
        "--format-id",
        default="https://eml.ecoinformatics.org/eml-2.2.0",
        help="FormatId for metadata (default: EML 2.2.0)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification for Dataverse requests (use only if you trust the server)",
    )
    args = parser.parse_args(argv)

    # 1. Export EML
    export_eml(args.base_url, args.persistent_id, args.api_key, args.metadata_out, insecure=args.insecure)

    # 2. Fetch dataset JSON to infer rights holder if not provided
    ds_json = fetch_dataset_json(args.base_url, args.persistent_id, args.api_key, insecure=args.insecure)
    rights_holder = pick_rights_holder(ds_json, args.rights_holder)

    # 3. Create sysmeta stub
    file_name = os.path.basename(args.metadata_out) or "metadata.xml"
    write_sysmeta_stub(
        identifier=args.persistent_id,
        authoritative_member_node=args.authoritative_member_node,
        rights_holder=rights_holder,
        file_name=file_name,
        out_path=args.sysmeta_out,
        format_id=args.format_id,
    )

    print("Prepared:")
    print(f"  metadata: {args.metadata_out}")
    print(f"  sysmeta : {args.sysmeta_out}")
    print("Next: run metadigpy -runcheck or -runsuite with these paths.")


if __name__ == "__main__":
    main()
