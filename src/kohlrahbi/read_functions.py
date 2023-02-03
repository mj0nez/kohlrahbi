"""
A collection of functions to get information from AHB tables.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Union

import pandas as pd
import pytz
from docx.document import Document  # type:ignore[import]
from docx.oxml.table import CT_Tbl  # type:ignore[import]
from docx.oxml.text.paragraph import CT_P  # type:ignore[import]
from docx.table import Table, _Cell  # type:ignore[import]
from docx.text.paragraph import Paragraph  # type:ignore[import]
from maus.edifact import EdifactFormatVersion, get_edifact_format_version

from kohlrahbi.ahbsubtable import AhbSubTable
from kohlrahbi.ahbtable import AhbTable
from kohlrahbi.logger import logger
from kohlrahbi.seed import Seed
from kohlrahbi.unfoldedahbtable import UnfoldedAhb


def get_all_paragraphs_and_tables(parent: Union[Document, _Cell]) -> Generator[Union[Paragraph, Table], None, None]:
    """
    Yield each paragraph and table child within *parent*, in document order.
    Each returned value is an instance of either Table or Paragraph.
    *parent* would most commonly be a reference to a main Document object, but
    also works for a _Cell object, which itself can contain paragraphs and tables.
    """
    # pylint: disable=protected-access
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Passed parent argument must be of type Document or _Cell")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


_validity_start_date_from_ahbname_pattern = re.compile(r"^.*(?P<germanLocalTimeStartDate>\d{8})\.docx$")
"""
https://regex101.com/r/g4wWrT/1
This pattern is strictly coupled to the edi_energy_scraper.
"""


def _get_format_version_from_ahbfile_name(ahb_docx_name: str) -> EdifactFormatVersion:
    """
    We try to extract the validity period of the AHB from its filename.
    The matching logic here is strictly coupled to the edi_energy_scraper.
    """
    match = _validity_start_date_from_ahbname_pattern.match(ahb_docx_name)
    berlin_local_time: datetime
    berlin = pytz.timezone("Europe/Berlin")
    if match:
        local_date_str = match.groupdict()["germanLocalTimeStartDate"]
        berlin_local_time = datetime.strptime(local_date_str, "%Y%m%d").astimezone(berlin)
    else:
        berlin_local_time = datetime.utcnow().astimezone(berlin)
    edifact_format_version = get_edifact_format_version(berlin_local_time)
    return edifact_format_version


def does_the_table_contain_pruefidentifikatoren(table: Table) -> bool:
    """
    Checks if the given table is a AHB table with pruefidentifikatoren.
    """

    return table.cell(row_idx=0, col_idx=0).text == "EDIFACT Struktur"


# pylint: disable=inconsistent-return-statements
def get_kohlrahbi(
    document: Document, root_output_directory_path: Path, ahb_file_name: Path, pruefi: str
) -> Optional[pd.DataFrame]:
    """Reads a docx file and extracts all information for each Prüfidentifikator.

    Args:
        document (Document): AHB which is read by python-docx package
        output_directory_path (Path): Location of the output files
        ahb_file_name (str): Name of the AHB document

    Returns:
        int: Error code, 0 means success
    """

    seed: Optional[Seed] = None
    edifact_format_version: EdifactFormatVersion = _get_format_version_from_ahbfile_name(str(ahb_file_name))
    logger.info("Extracted format version: %s", edifact_format_version)
    output_directory_path: Path = root_output_directory_path / str(edifact_format_version)
    logger.info("The output directory is: %s", output_directory_path)

    ahb_table_dataframe: Optional[pd.DataFrame] = None
    new_ahb_table: Optional[AhbTable] = None
    is_ahb_table_initialized: bool = False
    searched_pruefi_is_found: bool = False

    # Iterate through the whole word document
    logger.info("Start iterating through paragraphs and tables")
    for item in get_all_paragraphs_and_tables(parent=document):
        # Check if we reached the end of the current AHB document and stop if it's true.
        if isinstance(item, Paragraph) and "Heading" in item.style.name and "Änderungshistorie" in item.text:
            return None

        # Check if there is just a text paragraph,
        if isinstance(item, Paragraph) and not "Heading" in item.style.name:
            continue

        if isinstance(item, Table) and does_the_table_contain_pruefidentifikatoren(table=item):
            # check which pruefis
            seed = Seed.from_table(docx_table=item)
            logger.info("Found a table with the following pruefis: %s", seed.pruefidentifikatoren)

        we_reached_the_end_of_the_ahb_table_of_the_searched_pruefi: bool = (
            seed is not None and pruefi not in seed.pruefidentifikatoren and searched_pruefi_is_found
        )

        # @konstantin: Wie war nochmal die Reihenfolge in Python in der die Bedingungen geprüft werden?
        if we_reached_the_end_of_the_ahb_table_of_the_searched_pruefi:
            seed = None
            logger.info("🏁 We reached the end of the AHB table of the Prüfidentifikator '%s'", pruefi)
            break

        if isinstance(item, Table) and does_the_table_contain_pruefidentifikatoren(table=item):
            # check which pruefis
            seed = Seed.from_table(docx_table=item)
            logger.info("Found a table with the following pruefis: %s", seed.pruefidentifikatoren)

            if pruefi in seed.pruefidentifikatoren and not is_ahb_table_initialized:
                logger.info("👀 Found the AHB table with the Prüfidentifkator you are looking for %s", pruefi)
                searched_pruefi_is_found = True
                logger.info("✨ Initializing new ahb table dataframe")

                ahb_sub_table = AhbSubTable.from_table_with_header(docx_table=item)

                new_ahb_table = AhbTable.from_ahb_sub_table(ahb_sub_table=ahb_sub_table)

                is_ahb_table_initialized = True
                continue
        if isinstance(item, Table) and seed is not None and new_ahb_table is not None:
            ahb_sub_table = AhbSubTable.from_headless_table(docx_table=item, tmd=ahb_sub_table.table_meta_data)
            new_ahb_table.append_ahb_sub_table(ahb_sub_table=ahb_sub_table)

    if new_ahb_table is None:
        logger.warning("⛔️ Your searched pruefi '%s' was not found in the provided files.\n", pruefi)
        return None

    new_ahb_table.sanitize()

    unfolded_ahb = UnfoldedAhb.from_ahb_table(ahb_table=new_ahb_table, pruefi=pruefi)

    unfolded_ahb.convert_to_flat_ahb()

    return new_ahb_table.table