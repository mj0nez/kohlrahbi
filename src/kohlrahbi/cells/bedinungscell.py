"""
This module contains the class BedingungCell
"""

import re

import attrs
import pandas as pd
from docx.table import _Cell  # type:ignore[import]


# pylint:disable=too-few-public-methods
@attrs.define(auto_attribs=True, kw_only=True)
class BedingungCell:
    """
    BedingungCell contains all information and a method
    to extract the Bedingungen of an AHB Bedingung cell.
    """

    table_cell: _Cell

    def parse(self, ahb_row_dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Parses a cell in the Bedingung column and puts the information into the appropriate column of the dataframe

        Args:
            bedingung_cell (_Cell): Cell from the Bedingung column
            dataframe (pd.DataFrame): Saves all infos
        """

        bedingung = self.table_cell.text.replace("\n", " ")
        matches = re.findall(r"\[\d+\]", bedingung)
        for match in matches[1:]:
            index = bedingung.find(match)
            bedingung = bedingung[:index] + "\n" + bedingung[index:]

        row_index = ahb_row_dataframe.index.max()
        ahb_row_dataframe.at[row_index, "Bedingung"] += bedingung
        return ahb_row_dataframe