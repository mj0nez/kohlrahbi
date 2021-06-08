from enum import Enum
from typing import List


class row_type(Enum):
    SEGMENTNAME = 1
    SEGMENTGRUPPE = 2
    SEGMENT = 3
    DATENELEMENT = 4
    HEADER = 5
    EMPTY = 6


def is_row_header(text_in_row_as_list):
    if text_in_row_as_list[0] == "EDIFACT Struktur":
        return True

    return False


def is_row_segmentname(table, text_in_row_as_list: List) -> bool:
    """
    Checks if the actual row contains just the segment name like "Nachrichten-Kopfsegment"
    """

    if text_in_row_as_list[0] and not text_in_row_as_list[1] and not text_in_row_as_list[2]:
        return True

    return False


def is_row_segmentgruppe(edifact_struktur_cell):
    # if (
    #     not edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
    #     and not "\t" in edifact_struktur_cell.text
    # ):
    #     return True

    if (
        edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and not "\t" in edifact_struktur_cell.text
    ):
        return True

    return False


def is_row_segment(edifact_struktur_cell):
    # |   UNH    |
    if (
        not edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and not "\t" in edifact_struktur_cell.text
        and not edifact_struktur_cell.text == ""
    ):
        return True

    # | SG2\tNAD |
    if (
        edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and edifact_struktur_cell.text.count("\t") == 1
    ):
        return True

    return False


def is_row_datenelement(edifact_struktur_cell):
    # |   UNH\t0062 |
    if (
        not edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and "\t" in edifact_struktur_cell.text
    ):
        return True

    # | SG2\tNAD\t3035 |
    if (
        edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and edifact_struktur_cell.text.count("\t") == 2
    ):
        return True

    return False


def is_row_empty(edifact_struktur_cell):
    if edifact_struktur_cell.text == "":
        return True
    return False


def define_row_type(table, edifact_struktur_cell, text_in_row_as_list):
    if is_row_header(text_in_row_as_list=text_in_row_as_list):
        return row_type.HEADER

    elif is_row_segmentname(table=table, text_in_row_as_list=text_in_row_as_list):
        return row_type.SEGMENTNAME

    elif is_row_segmentgruppe(edifact_struktur_cell=edifact_struktur_cell):
        return row_type.SEGMENTGRUPPE

    elif is_row_segment(edifact_struktur_cell=edifact_struktur_cell):
        return row_type.SEGMENT

    elif is_row_datenelement(edifact_struktur_cell=edifact_struktur_cell):
        return row_type.DATENELEMENT

    elif is_row_empty(edifact_struktur_cell=edifact_struktur_cell):
        return row_type.EMPTY

    else:
        raise NotImplemented(f"Could not define row type of {text_in_row_as_list}")