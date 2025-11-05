"""Metadig metadata utilities"""

import xml.etree.ElementTree as ET
import io
import hashlib
import pandas
import chardet
import re

try:
    from java.util import ArrayList
except ImportError:
    # If there is an issue with importing python recognized java classes from
    # the Jython environment, we will attempt to create the classes necessary
    # to proceed with the check.
    from metadig.checks import ListWithGet as ArrayList


def read_sysmeta_element(stream, element):
    """
    Reads and parses a stream of system metadata to find and return the text value
    of a specified element.

    Args:
        stream (BufferedReader): A stream containing system metadata.
        element (str): The name of the element to retrieve.

    Returns:
        str or None: The text content of the found element, or None if not found.

    Raises:
        ValueError: If there is an error parsing the sysmeta or if the specified
        element is not found.
    """
    try:
        # Parse the XML from the buffered reader
        stream.seek(0)
        tree = ET.parse(stream)
        root = tree.getroot()

        # Find the specified element and return its text value
        for elem in root.findall(element):
            return elem.text

    except ET.ParseError as e:
        raise ValueError(
            f"Error parsing XML: {e}, could not find element {element}"
        ) from e


def find_eml_entity(doc, identifier, file_name):
    """
    Searches through a string EML document to find and return dataTable and otherEntity elements
    that matches the identifier or fileName according to specified priority. The function will
    try to match first from identifier to the id element, then by file_name to entityName, then
    to objectName.

    Args:
        doc (str): XML document as a string.
        identifier (str): Identifier to match against the id element.
        file_name (str): File name to match against the entityName or objectName elements.

    Returns:
        xml.etree.Element: The XML element (dataTable or otherEntity) that matches the
        identifier or file_name, according to the specified priority (id, entityName, objectName).
        Returns None if no match is found.
    """

    # extract lists into single items
    list_types = (list, ArrayList)

    if isinstance(file_name, list_types):
        file_name = file_name[0]

    if isinstance(identifier, list_types):
        identifier = identifier[0]

    root = ET.fromstring(doc)

    # Search through dataTable and otherEntity elements
    for element in root.findall(".//dataTable") + root.findall(".//otherEntity"):
        # Check if identifier matches the id element
        id_attr = element.attrib.get("id")
        if id_attr is not None and id_attr == identifier.replace(":", "-"):
            return element

        # Check if fileName matches the entity name element
        entity_name_elem = element.find(".//entityName")
        if entity_name_elem is not None and entity_name_elem.text == file_name:
            return element

        # Check if fileName matches the object name element
        object_name_elem = element.find(".//objectName")
        if object_name_elem is not None and object_name_elem.text == file_name:
            return element

    # Return None if no match is found
    return None


def get_valid_csv(manager, pid):
    """
    Returns an input stream for a given pid if the file is a csv file, along with its
    filename and a status.

    Args:
        manager: a store manager returned from StoreManager()
        pid (str): Identifier of file to return.

    Returns:
        obj: An input stream object
        fname: The filename of the object
        status: SKIP or VALID. Returns skip if not a csv.

    """
    obj, sys = manager.get_object(pid)
    try:
        fname = read_sysmeta_element(sys, "fileName")
        if read_sysmeta_element(sys, "formatId") != "text/csv":
            return None, fname, "SKIP"
    finally:
        sys.close()
    return obj, fname, "VALID"


def find_entity_index(fname, pid, entity_names, ids):
    """
    Finds the index of a documented entity from a list of entities in a metadata document. The
    function will first try to match based on filename, then identifier. Returns none if no match.

    Args:
        fname (str): Filename of the file to match.
        pid (str): Identifier of file to match.
        entity_names: List of entity names to search for filename in
        ids: List of identifiers to search for identifier in

    Returns:
        z: Index of matching entity in documentation.

    """
    # Box up single items into a list for interating later
    list_types = (list, ArrayList)

    ids_l = ids if isinstance(ids, list_types) else [ids]
    entity_names_l = (
        entity_names if isinstance(entity_names, list_types) else [entity_names]
    )

    # Checks all elements in entity_names to find matches with fname
    z = [i for i, x in enumerate(entity_names_l) if x == fname]
    # If z is empty, we will try to match by pid instead
    if not z:
        z = [i for i, x in enumerate(ids_l) if x == pid.replace(":", "-")]

    return z[0] if z else None


def read_csv_with_metadata(
    d_read, fd, header_line, d_encoding=None, nan_filter=False, dtype_string=False
):
    """Uses pandas to read in a csv with given field delimiter and header rows to skip

    :param str or bytes d_read: RData as read in from the stream
    :param str fd: field delimiter from metadata
    :param int header_line: Number of rows to skip
    :param str d_encoding: Encoding type to use to read the given bytes
    :param bool nan_filter: Whether to detect missing value markers
    :param bool dtype_string: Whether to coerce all column types to string

    :return: A tuple containing:
        - df: Pandas data.frame with data
        - error: error message on exception
    """
    # Ensure fd is an int or str
    if isinstance(fd, list):
        fd = fd[0]  # Extract first element if list
    if not isinstance(fd, (str, int)):
        fd = ","  # Default to comma if invalid type
    # Ensure nan_filter is a boolean
    if not isinstance(nan_filter, bool):
        raise ValueError("Argument 'nan_filter' must be a boolean")

    if dtype_string == True:
        ty = str
    else:
        ty = None

    pd_header_val = 0
    if isinstance(header_line, list):
        # When a list is provided, the expectation is that this value is coming from the sysmeta
        # We will extract the first element and cast it into an integer, this number is usually 1
        try:
            first_element_from_list = int(header_line[0])
        except (ValueError, TypeError) as vte:
            raise ValueError(
                f"Unable to retrieve a numeric value from skiprows. Details: {vte}"
            ) from vte
        # We subtract 1 to standardize this value to pass onto pandas.read_csv
        pd_header_val = max(
            0, first_element_from_list - 1
        )  # Ensure it is never negative
    elif isinstance(header_line, int):
        if header_line > 0:
            pd_header_val = header_line - 1
    else:
        error_msg = (
            "Unable to read CSV, cannot determine 'header_line'. It must be an integer."
            + f" Detected type: {type(header_line)}. Value: {header_line}"
        )
        return None, error_msg

    try:
        if d_encoding is not None:
            return (
                pandas.read_csv(
                    io.StringIO(d_read),
                    delimiter=fd,
                    skiprows=pd_header_val,
                    encoding=d_encoding,
                    na_filter=nan_filter,
                    dtype=ty,
                ),
                None,
            )
        else:
            return (
                pandas.read_csv(
                    io.StringIO(d_read),
                    delimiter=fd,
                    skiprows=pd_header_val,
                    na_filter=nan_filter,
                ),
                None,
            )
    # pylint: disable=W0718
    except Exception as e:
        return None, f"Error reading CSV: {str(e)}"


def find_duplicate_column_names(pandas_df: pandas.DataFrame):
    """Find duplicate columns names in a text delimited file.

    :param df pandas_df: Data frame to check for duplicate columns
    :return: A tuple containing:
        - A list of (duplicate_column, original_column) pairs
        - A boolean indicating whether any column names contained periods
    :rtype: Tuple
    """
    # When pandas reads a .csv, it renames a duplicate column and appends: .#
    column_names = pandas_df.columns
    columns_to_check = column_names
    contains_period = any("." in col for col in column_names)

    if contains_period:
        # So we get a new list that substrings everything before the '.' to check for duplicates
        columns_to_check = [col.rsplit(".", 1)[0] for col in column_names]
    # Check the columns
    checked_cols_names = set()
    duplicate_col_names = set()
    for col in columns_to_check:
        if col in checked_cols_names:
            duplicate_col_names.add(col)
        checked_cols_names.add(col)

    return duplicate_col_names, contains_period


def find_duplicate_column_content(pandas_df: pandas.DataFrame):
    """Find duplicate columns in a text delimited file by calculating the hash of the column.

    :param df pandas_df: Data frame to check for duplicate columns
    :return: List of tuples of the duplicate columns. Each tuple shows the name of the
        duplicate columns and the calculated hash.
    """

    def hash_series(series):
        """Get the hash based on the column's values, ignoring the index"""
        return hashlib.md5(
            pandas.util.hash_pandas_object(series, index=False).values
        ).hexdigest()

    # Empty dict to store each unique column
    seen_hashes = {}
    # List to hold pairs (tuples) of columns
    duplicates = []

    for col in pandas_df.columns:
        # Get the unique hash value
        col_hash = hash_series(pandas_df[col])
        # Check to see if this hash is present, indicating a duplicate column
        if col_hash in seen_hashes:
            duplicates.append((col, seen_hashes[col_hash], col_hash))
        else:
            # Store this into the list of seen hashes
            seen_hashes[col_hash] = col

    return duplicates


def find_duplicate_rows(pandas_df: pandas.DataFrame):
    """Find duplicate rows in a text delimited file.

    :param df pandas_df: Data frame to check for duplicate rows
    :return: List of tuples of the duplicate columns. Each tuple shows the name of the
        duplicate columns and the calculated hash.
    :rtype: List
    """
    duplicates = pandas_df[pandas_df.duplicated(keep=False)]
    if duplicates.empty:
        return None
    else:
        return duplicates


def find_number_of_columns(pandas_df: pandas.DataFrame):
    """Find the number of columns in a text delimited file.

    :param df pandas_df: Data frame to check for duplicate rows
    :return: The number of columns in an integer
    :rtype: int
    """
    return pandas_df.shape[1]


def detect_text_encoding(raw: bytes):
    """Determine the encoding of the given bytes and return problematic sequences if
    found.

    :param bytes raw: Raw byte content
    :return: A tuple containing:
        - encoding (str): One of 'ascii', 'utf-8', or 'other'
        - error (str or None): None if decoding succeeded, or a string with error details
    :rtype: tuple
    """
    # First detect the encoding type
    detected_encoding_result = chardet.detect(raw)
    encoding = detected_encoding_result.get("encoding")
    # Now try to decode it
    try:
        raw.decode(encoding)
        return encoding, None
    # pylint: disable=W0612
    except UnicodeDecodeError as e:
        # If there an a decoding error, return the identified encoding type and the confidence
        # level, along with details on where we ran into the error.
        confidence = detected_encoding_result.get("confidence")
        encoding_msg = (
            "A decoding error has been detected while attempting to decode the document"
            + f" with detected encoding: {encoding}. Confidence level of encoding type:"
            + f" {round(confidence*100, 2)}%. Error Details:"
            + f" Error at byte {e.start}: {raw[e.start:e.end]}"
        )
        return encoding, encoding_msg


def escape_for_markdown(string: str):
    """Parses a string and escapes any of the following special characters
    so that the string is displayed properly in markdown: \\`*_{}[]<>()#+-.!|

    :param string str: String to sanitize
    :return: A string with special character escaped
    :rtype: string
    """
    markdown_chars_to_escape = set(r"\`*_{}[]<>()#+-.!|")
    return "".join(
        f"\\{character}" if character in markdown_chars_to_escape else character
        for character in string
    )
