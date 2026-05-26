"""Metadig check utilities"""

import json
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from lxml import etree


def getType(object_to_check):
    """Checks and prints the argument's object type."""
    print("type: {}".format(type(object_to_check)))


def isResolvable(url):
    # First parse the url for a protocol, host port and path
    """Function that checks if a url is resolvable

    The function first checks if the url uses HTTP protocols, which is
    currently the only protocol supported.

    Args:
        url - the url to check for resolvability

    Returns:
        list: the first element is either True or False (i.e. is/is not resolvable)
              the second element is a status message, describing success or an error message.

    """
    # url = 'https://cn.dataone.org/cn/v2/resolve/urn:uuid:7098ba54-ca6f-4e35-beb3-718bd0fe58a8'
    url_comps = urlparse(url)
    if url_comps.netloc == "":
        return (False, '"{}" does not appear to be a URL'.format(url))

    # Check the 'schema' to see if it is an open one. Currently we
    # are just check for http and https.
    known_protocols = ["http", "https"]
    if url_comps.scheme not in set(known_protocols):
        return (
            False,
            'Unknown or proprietary communications protocol: "{}", known protocols: {}'.format(
                url_comps.scheme, ", ".join(known_protocols)
            ),
        )

    # Perform an HTTP 'Head' request - we just want to know if the file exists and do not need to
    # download it.
    request = urllib.request.Request(url)
    request.get_method = lambda: "HEAD"
    # Python urllib2 strangely throws an error for an http status, and the response object is
    # returned by the exception code.
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as he:
        # An error was encountered resolving the url, check which one so that we can print
        # a more meaningful error message than provided by HTTPError
        # FYI, HTTP status codes from FAIR FM_A1.1
        # (https://github.com/FAIRMetrics/Metrics/blob/master/Distributions/FM_A1.1.pdf)
        if he.code == 400:
            return (False, "Unable to resolved URL {}: Bad request".format(url))
        elif he.code == 401:
            return (False, "Unable to resolved URL {}: Unauthorized".format(url))
        elif he.code == 404:
            return (False, "Unable to resolved URL {}: Not Found".format(url))
        elif he.code == 500:
            return (False, "Unable to resolved URL {}: Server Error".format(url))
        else:
            return (
                False,
                'Error resolving URL "{}": {} {}'.format(url, he.code, he.headers),
            )
    except urllib.error.URLError as ue:
        return (False, ue.reason[1])
    except OSError as oe:
        return (False, repr(oe))
    # pylint: disable=W0718
    except Exception as e:
        return (False, repr(e))
    # Disabling this warning for legacy code
    # pylint: disable=W0702
    except:
        return (False, "Unexpected error:", sys.exc_info()[0])

    response.close()
    if response.code in set([200, 202, 203, 206, 301, 302, 303, 307, 308]):
        return (
            True,
            "Successfully resolved the URL {}: status {}".format(url, response.code),
        )
    else:
        return (False, "Did not resolved the URL {}".format(url))


def get_data_pids(identifier: str, member_node: str):
    """Retrieve the associated data pids for the given pid by querying the appropriate
    member node's solr end point.

    :param str identifier: The persistent identifier to retrieve data pids for
    :param str member_node: The member node whose URL to query (ex. 'urn:node:ARCTIC')
    :return: List of data pids
    """
    member_node_url = get_member_node_url(member_node)
    encoded_identifier = urllib.parse.quote(identifier)
    solr_query = f"/query/solr/?q=isDocumentedBy:%22{encoded_identifier}%22&fl=id"
    query_url = member_node_url + solr_query

    try:
        # Create a request and parse response for the associated data pids (objects)
        req = urllib.request.Request(query_url)

        # Send the request and read the response
        with urllib.request.urlopen(req) as response:
            # Read and decode the response
            xml_bytes = response.read()
            # pylint: disable=I1101
            root = etree.fromstring(xml_bytes)

    except Exception as ge:
        raise RuntimeError(f"Unexpected exception encountered: {ge}") from ge

    # Iterate over the doc list and return a list of the data pids
    data_pids = [
        elem.text
        for elem in root.xpath('//doc/str[@name="id"]')
        if elem.text != identifier
    ]
    return data_pids


def get_member_node_url(member_node: str):
    """Retrieve the associated member node's baseUrl from the CN. Note, we append '/v2'
    to the Base URL retrieved.

    :param str member_node: The persistent identifier to retrieve data pids for
    :return: baseUrl to the member node
    """
    try:
        url = "https://cn.dataone.org/cn/v2/node"

        # Create and send the request
        req = urllib.request.Request(url)

        with urllib.request.urlopen(req) as response:
            data = response.read().decode("utf-8")
            # Convert the string to bytes so lxml can parse it
            xml_bytes = data.encode("utf-8")
            # pylint: disable=I1101
            root = etree.fromstring(xml_bytes)

    except Exception as ge:
        raise RuntimeError(f"Unexpected exception encountered: {ge}") from ge

    # Find the matching node and return its baseURL
    for node in root.findall(".//node"):
        node_id = node.findtext("identifier")
        if node_id == member_node:
            base_url = node.findtext("baseURL")
            v2_base_url = base_url + "/v2"
            return v2_base_url
    raise ValueError(f"Base Url not found for member node: {member_node}.")


def get_sysmeta_vars(sysmeta_path: str):
    """Parse the given sysmeta path and retrieve the identifier, authoritative_member_node,
    rights_holder, date_uploaded, format_id and obsoletes

    :param str sysmeta_path: Path to the system metadata document to read
    :return: Dictionary containing an identifier and member node value
    """
    # pylint: disable=I1101
    sysmeta_doc_root = etree.parse(sysmeta_path).getroot()
    try:
        identifier = sysmeta_doc_root.find("identifier").text
        authoritative_member_node = sysmeta_doc_root.find(
            "authoritativeMemberNode"
        ).text
        rights_holder = sysmeta_doc_root.find("rightsHolder").text
        date_uploaded = sysmeta_doc_root.find("dateUploaded").text
        format_id = sysmeta_doc_root.find("formatId").text
        if identifier is None:
            raise ValueError("Element 'identifier' is missing from sysmeta document")
        if authoritative_member_node is None:
            raise ValueError(
                "Element 'authoritativeMemberNode' is missing from sysmeta document"
            )
    except AttributeError as ae:
        raise AttributeError(
            "Elements 'identifier' or 'authoritativeMemberNode' is missing from sysmeta document"
        ) from ae

    try:
        obsoletes = sysmeta_doc_root.find("obsoletes").text
    except Exception:
        obsoletes = None

    sm_rn_vars = {}
    sm_rn_vars["identifier"] = identifier
    sm_rn_vars["authoritative_member_node"] = authoritative_member_node
    sm_rn_vars["rights_holder"] = rights_holder
    sm_rn_vars["date_uploaded"] = date_uploaded
    sm_rn_vars["format_id"] = format_id
    sm_rn_vars["obsoletes"] = obsoletes
    return sm_rn_vars


def run_check(
    check_xml_path: str,
    metadata_xml_path: str,
    metadata_sysmeta_path: str,
    store_props: Optional[Dict[str, Any]] = None,
):
    """
    Run a validation check against an XML metadata document.

    :param str check_xml_path: Path to the XML file containing the check configuration.
    :param str metadata_xml_path: Path to the XML metadata document.
    :param str metadata_sysmeta_path: Path to the sysmeta for the XML metadata document
    :param Dict store_props: Dictionary containing the store properties: store_type, store_path,
        store_depth, store_width, store_algorithm, store_metadata_namespace
    :return: The result of the check function.
    """
    # Load the metadata and check XML files
    # pylint: disable=I1101
    metadata_doc = etree.parse(metadata_xml_path).getroot()
    metadata_doc_no_ns = etree.parse(metadata_xml_path).getroot()

    # Remove namespaces
    for elem in metadata_doc_no_ns.iter():
        if elem.tag.startswith("{") and not elem.tag.startswith(
            "{http://www.w3.org/2001/XMLSchema-instance}"
        ):
            elem.tag = elem.tag.split("}", 1)[1]

    # Load the check XML & ensure the check is valid
    check_doc = etree.parse(check_xml_path).getroot()
    check_id_elem = check_doc.xpath(".//id")
    check_id = check_id_elem[0].text if check_id_elem else "Unknown"
    if not is_check_valid(check_doc, metadata_doc):
        print(
            f"Check {check_id} is not valid for metadata document {metadata_xml_path}"
        )
        return

    # Extract selectors and apply them
    selectors = check_doc.xpath(".//selector")
    if not selectors:
        raise ValueError("No selectors are defined for this check.")

    # Prepare check variables
    check_vars = {}
    sysmeta_check_vars = get_sysmeta_vars(metadata_sysmeta_path)
    identifier = sysmeta_check_vars.get("identifier")
    auth_mn_node = sysmeta_check_vars.get("authoritative_member_node")
    
    # Try to get data PIDs from DataONE, but don't fail if network is unavailable
    try:
        data_pids = get_data_pids(identifier, auth_mn_node)
    except Exception:
        # If we can't reach DataONE (network issues, SSL errors, etc.),
        # just use an empty list. Most metadata checks don't need data PIDs.
        data_pids = []
    
    # TODO: Potential Optimization Point
    # `variables-congruent` is the only check at this time that requires it, and seems
    # like we're adding a lot of overhead for just one check.
    # if "data.table-text-delimited.variables-congruent" == check_id:
    document = Path(metadata_xml_path).read_text(encoding="utf-8")
    check_vars["document"] = document
    check_vars["dataPids"] = data_pids
    check_vars["storeConfiguration"] = store_props
    # read in the sysmeta and add it to check vars as a string
    with open(metadata_sysmeta_path, "r", encoding="utf-8") as f:
        metadata_sysmeta_read = f.read()
    check_vars["systemMetadata"] = metadata_sysmeta_read
    # add in mdq params
    resources_dir = (Path(__file__).parent.parent / "metadig/resources").resolve()
    check_vars["mdq_params"] = {
        "metadigDataDir": resources_dir,
    }
    # Extract the information from selectors
    for selector in selectors:
        # selector_xpath = selector.xpath("xpath")[0].text
        selector_name = selector.xpath("name")[0].text
        ns_aware_elem = selector.get("namespaceAware")
        ns_aware = ns_aware_elem and ns_aware_elem[0].text.lower() == "true"
        metadata_doc_to_use = metadata_doc if ns_aware else metadata_doc_no_ns
        variable_list = select_nodes(metadata_doc_to_use, selector)
        check_vars[selector_name] = variable_list

    # Execute check function
    code_elem = check_doc.xpath("code")
    if code_elem:
        exec_code_string = code_elem[0].text + "\ncall()"
        try:
            # pylint: disable=W0122
            exec(exec_code_string, check_vars)
            metadigpy_result = check_vars.get("metadigpy_result")
            if metadigpy_result is None:
                # If there is no metadigpy_result, it is not a data-suite check, so we
                # fallback to the existing global variables.
                fallback = {
                    "output": check_vars.get("output", "No output."),
                    "status": check_vars.get("status", "FAILURE"),
                }
                json_output = json.dumps(fallback, indent=4)
            else:
                json_output = json.dumps(metadigpy_result, indent=4)
            return json_output
        # pylint: disable=W0718
        except Exception as e:
            exception_output = {}
            exception_output["identifiers"] = [data_pids]
            exception_output["output"] = [
                f"Unexpected exception while running check: {e}"
            ]
            exception_output["status"] = "ERROR"
            json_output = json.dumps(exception_output, indent=4)
            return json_output
    else:
        raise IOError("Check code is unavailable/cannot be found.")


def try_run_check(obj_tuple):
    """Executes a 'run_check' function in a try block that can be called by multiprocessing.

    :param str obj_tuple: a tuple containing the arguments for the 'run_check' function:
        check_xml_path, metadata_xml_path, metadata_sysmeta_path, store_props
    :return: The results of the check, and the check_id, and an additional message
    """
    try:
        check_id = obj_tuple[0].rsplit("/", 1)[-1]
        result = run_check(*obj_tuple)
        return result, check_id, None
    # pylint: disable=W0718
    except Exception as so_exception:
        check_id = obj_tuple[0].rsplit("/", 1)[-1]
        return None, check_id, str(so_exception)


def is_check_valid(check_doc, metadata_doc):
    """
    Check if the given check document is valid for the metadata document.

    :param check_doc: XML representing the check document.
    :param metadata_doc: XML representing the metadata document.
    :return: True if valid, False otherwise.
    """
    dialect_nodes = check_doc.xpath("dialect")
    if dialect_nodes:
        for dialect_node in dialect_nodes:
            dialect_name_elem = dialect_node.xpath("name")
            dialect_xpath_elem = dialect_node.xpath("xpath")

            if dialect_name_elem and dialect_xpath_elem:
                dialect_xpath = dialect_xpath_elem[0].text
                dialect_match_node = metadata_doc.xpath(dialect_xpath)

                if dialect_match_node:
                    return True
        return False
    # If no dialect specified, assume check is valid for all metadata
    return True


def ns_strip(xml_doc, ns_prefix):
    """
    Strip the specified namespace from a document.

    :param xml_doc: The document to strip.
    :param ns_prefix: The namespace prefix to strip.
    :return: XML document without the specified namespace.
    """
    xpath_str = f".//namespace::*[name()='{ns_prefix}']/parent::*"
    for element in xml_doc.xpath(xpath_str):
        ns_decl = f"xmlns:{ns_prefix}"
        if ns_decl in element.attrib:
            del element.attrib[ns_decl]
    return xml_doc


def select_nodes(context_node, selector_context):
    """
    Select data values from a metadata document as specified in a check's selectors.

    :param context_node: Metadata document node.
    :param selector_context: Selector node defining the extraction criteria.
    :return: List of selected node values.
    """
    if selector_context is None:
        return []
    values = ListWithGet()
    # The main xpath string
    selector_xpath = selector_context.xpath("xpath")[0].text
    # A list of sub_selector nodes
    sub_selector = selector_context.xpath("subSelector")

    # Apply the xpath, selecting the top-level nodes to check
    selected_nodes = context_node.xpath(selector_xpath)

    # At this point, selected_nodes could be a list of nodes, an empty list or a boolean
    if isinstance(selected_nodes, bool):
        # If it's a boolean, wrap the result of the expression into a list
        return [selected_nodes]
    if not selected_nodes:
        # If it's empty or false, return an empty list of values
        return values

    for node in selected_nodes:
        if sub_selector:
            value = select_nodes(node, sub_selector[0])
        else:
            # If there is no sub_selector, we extract the final value
            if hasattr(node, "text") and node.xpath("string()").strip() is not None:
                text_val = node.xpath("string()").strip()
            else:
                text_val = node
            try:
                value = float(text_val)
            except (ValueError, TypeError):
                if text_val == "True":
                    value = True
                elif text_val == "False":
                    value = False
                else:
                    value = text_val
        # 'select_nodes(...)' always return a list. So if a 'sub_selector' is involved
        # and the recursion completes, we end up with a list that we either keep or try to
        # convert to a float or boolean. If we keep this list, we do not want to return a nested
        # list inside of 'values' - so we extend the values with the contents of the list.
        # The existing checks expect a flat list, and do not account for nested lists.
        if isinstance(value, list):
            values.extend(value)
        else:
            values.append(value)
    return values


class ListWithGet(list):
    """This custom list class supports .get access on a list to mimic a dictionary,
    which adds compatibility with existing check code."""

    def get(self, index, default=None):
        """Retrieve the element at the given index. If the index is out of bounds,
        return the provided default value (None)."""
        try:
            return self[index]
        except IndexError:
            return default
