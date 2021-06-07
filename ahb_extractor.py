from pathlib import Path
from typing import List

import docx
import numpy as np
import pandas as pd

directory_path = Path.cwd() / "documents"
file_name = "UTILMD_AHB_WiM_3_1c_2021_04_01_2021_03_30.docx"

path_to_file = directory_path / file_name

from enum import Enum


class row_type(Enum):
    SEGMENTNAME = 1
    SEGMENTGRUPPE = 2
    SEGMENT = 3
    DATENELEMENT = 4
    HEADER = 5


def create_list_of_column_indices(table):
    """
    The amount of columns of the tables can switch between 3 and 4.
    If the actual table contains the header with "EDIFACT Struktur", then the table has 4 columns.
    The second and the third one have exactly the same content. So we skip the third one to get the same length for the list.
    """
    number_of_columns: int = table._column_count

    if number_of_columns == 3:
        return [0, 1, 2]
    elif number_of_columns == 4:
        return [0, 1, 3]
    else:
        raise NotImplemented(
            f"Only tables with 3 and 4 columns are implemented. Your table has {number_of_columns} columns."
        )


def write_segment_name_to_dataframe(final_dataframe, row_index, dataframe_row, text_in_row_as_list):
    dataframe_row[0] = text_in_row_as_list[0]
    final_dataframe.loc[row_index] = dataframe_row


def write_segmentgruppe_to_dataframe(final_dataframe, row_index, dataframe_row, text_in_row_as_list):
    dataframe_row[0] = text_in_row_as_list[0]

    if text_in_row_as_list[1].count("\t") == 3:
        # example for text_in_row_as_list: ['SG2', '\tMuss\tMuss\tMuss', '']
        splitted_middle_column = text_in_row_as_list[1].split("\t")
        dataframe_row[5] = splitted_middle_column[1]
        dataframe_row[6] = splitted_middle_column[2]
        dataframe_row[7] = splitted_middle_column[3]

    final_dataframe.loc[row_index] = dataframe_row


def write_segment_to_dataframe(final_dataframe, row_index, dataframe_row, text_in_row_as_list):
    splitted_edifact_struktur_cell = text_in_row_as_list[0].split("\t")
    dataframe_row[0] = splitted_edifact_struktur_cell[0]
    dataframe_row[1] = splitted_edifact_struktur_cell[1]

    splitted_middle_cell = text_in_row_as_list[1].split("\t")
    if text_in_row_as_list[1].count("\t") == 3:
        dataframe_row[5] = splitted_middle_cell[1]
        dataframe_row[6] = splitted_middle_cell[2]
        dataframe_row[7] = splitted_middle_cell[3]

    final_dataframe.loc[row_index] = dataframe_row


def parse_first_paragraph_in_middle_column_to_dataframe(paragraph, dataframe_row):

    # Codenummer, e.g. 332 or
    # Freitext, e.g. Vorgangsnummer

    splitted_text_at_tabs = paragraph.text.split("\t")

    # Qualifier / Code
    dataframe_row[3] += splitted_text_at_tabs.pop(0)

    for tabstop in paragraph.paragraph_format.tab_stops._pPr.tabs:
        if tabstop.pos == 436245:
            # Beschreibung
            dataframe_row[4] += splitted_text_at_tabs.pop(0)
        elif tabstop.pos == 1962785:
            # first Prüfidentifikator
            dataframe_row[5] += splitted_text_at_tabs.pop(0)
        elif tabstop.pos == 2578735:
            # second Prüfidentifikator
            dataframe_row[6] += splitted_text_at_tabs.pop(0)
        elif tabstop.pos == 3192780:
            # third Prüfidentifikator
            dataframe_row[7] += splitted_text_at_tabs.pop(0)
        else:
            raise NotImplementedError(
                f"Found an undefined tabstop position: {tabstop.pos}. Text: {splitted_text_at_tabs}"
            )
    return dataframe_row


# def parse_multiline_ahb_condition_expression(paragraph, dataframe_row):
#     """
#     Example:
#     Muss ([77]	Muss ([59]	Muss [61] U
# 	U [78]) U	U [580]) O	[584]
# 	(([61] U	([46] U [61])
# 	[584]) O
# 	[583])

#     """


def write_dataelement_to_dataframe(final_dataframe, row_index, dataframe_row, text_in_row_as_list, middle_cell):

    splitted_edifact_struktur_cell = text_in_row_as_list[0].split("\t")
    if text_in_row_as_list[0].count("\t") == 1:
        # EDIFACT Struktur column: UNH\t0062
        dataframe_row[1] = splitted_edifact_struktur_cell[0]
        dataframe_row[2] = splitted_edifact_struktur_cell[1]
    elif text_in_row_as_list[0].count("\t") == 2:
        dataframe_row[0] = splitted_edifact_struktur_cell[0]
        dataframe_row[1] = splitted_edifact_struktur_cell[1]
        dataframe_row[2] = splitted_edifact_struktur_cell[2]

    # here we can also distinguish between Freitext (graue Schrift Felder) und nicht Freitext (fette geschriebene Felder)
    # if middle_cell.paragraphs[0].runs[0].bold:

    if len(middle_cell.paragraphs) == 1:
        # -> single line row
        dataframe_row = parse_first_paragraph_in_middle_column_to_dataframe(
            paragraph=middle_cell.paragraphs[0], dataframe_row=dataframe_row
        )
    else:
        for paragraph in middle_cell.paragraphs:
            if paragraph.paragraph_format.left_indent == 36830 and "\t" in paragraph.text:
                # Beschreibung -> 4 -> 436245
                # 11039 -> 5 -> 1962785
                # 11040 -> 6 -> 2578735
                # 11041 -> 7 -> 3192780

                dataframe_row = parse_first_paragraph_in_middle_column_to_dataframe(
                    paragraph=paragraph, dataframe_row=dataframe_row
                )

            elif paragraph.paragraph_format.left_indent == 36830 and not "\t" in paragraph.text:
                # multi line Freitext
                dataframe_row[3] += " " + paragraph.text
            elif paragraph.paragraph_format.left_indent == 436245:
                # multi line Beschreibung
                dataframe_row[4] += " " + paragraph.text
            elif paragraph.paragraph_format.left_indent is None:
                parse_first_paragraph_in_middle_column_to_dataframe(paragraph=paragraph, dataframe_row=dataframe_row)
            else:
                raise NotImplementedError(f"The row with {repr(paragraph.text)} can not be read.")

    final_dataframe.loc[row_index] = dataframe_row


def has_cell_in_edifact_struktur_column_a_segmentgruppe(cell):
    """
    Checks if the cell contains a Segementgruppe like e.g. "SG2" or "SG2\tNAD\t3035"
    (should only be called for cells in EDIFACT Struktur column)
    """
    # if cell.paragraphs[0].paragraph_format.left_indent == 364490:
    if cell.paragraphs[0].paragraph_format.left_indent == 36830:
        return True
    return False


def is_cell_in_middle_column_a_dataelement(cell):
    # IDEE: ERSTELLE FUNKTION DIE BEREITS DIE GESAMTE ZEILE PRÜFT; WAS SIE IST
    # * segment name: MP-ID Absender
    # * segment gruppe: SG2
    # * segment: SG2\tNAD
    # * datenelement: SG2\tNAD\t3035
    pass


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
    if (
        not edifact_struktur_cell.paragraphs[0].paragraph_format.left_indent == 36830
        and not "\t" in edifact_struktur_cell.text
    ):
        return True

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
    else:
        raise NotImplemented(f"Could not define row type of {text_in_row_as_list}")


def main():
    try:
        doc = docx.Document(path_to_file)  # Creating word reader object.

        # TODO for each section get header to get prüfidentifaktoren for dataframe header

        actual_df_row_index: int = 0
        # df = pd.DataFrame(columns=["text", "tab1", "tab2", "tab3", "tab4", "tab5"])
        df = pd.DataFrame(
            columns=[
                "Segment Gruppe",
                "Segment",
                "Datenelement",
                "Codes und Qualifier",
                "Beschreibung",
                "11039",  # should be taken from table header
                "11040",  # should be taken from table header
                "11041",  # should be taken from table header
                "Bedingung",
            ],
            dtype="str",
        )

        # for table in doc.tables[2 : len(doc.tables)]:
        for table in doc.tables[1:20]:

            column_indices = create_list_of_column_indices(table=table)

            for row in range(len(table.rows)):

                index_for_middle_column = 1
                # initial empty list for the next row in the dataframe
                actual_dataframe_row = (len(df.columns)) * [""]

                # idea: cause of double information in 4 column tables, remove entry [2] from row_cell_texts_as_list
                row_cell_texts_as_list = [cell.text for cell in table.row_cells(row)]
                if table._column_count == 4:
                    # remove redundant information for tables with 4 columns
                    if (
                        row_cell_texts_as_list[0] == row_cell_texts_as_list[1]
                        and row_cell_texts_as_list[2] == row_cell_texts_as_list[3]
                    ):
                        # HEADER looks like
                        # 0:'EDIFACT Struktur'
                        # 1:'EDIFACT Struktur'
                        # 2:'Beschreibung\tKündigung\tBestätigung\tAblehnung\tBedingung\n\tMSB \tKündigung\tKündigung\n\tMSB \tMSB \nKommunikation von\tMSBN an\tMSBA an\tMSBA an\n\tMSBA\tMSBN\tMSBN\nPrüfidentifikator\t11039\t11040\t11041'
                        # 3:'Beschreibung\tKündigung\tBestätigung\tAblehnung\tBedingung\n\tMSB \tKündigung\tKündigung\n\tMSB \tMSB \nKommunikation von\tMSBN an\tMSBA an\tMSBA an\n\tMSBA\tMSBN\tMSBN\nPrüfidentifikator\t11039\t11040\t11041'
                        # len():4
                        del row_cell_texts_as_list[1]
                        row_cell_texts_as_list[2] == ""
                    elif row_cell_texts_as_list[0] == row_cell_texts_as_list[1] and row_cell_texts_as_list[3] == "":
                        # Dataelement row with header in the table
                        # 0:'SG2\tNAD\t3035'
                        # 1:'SG2\tNAD\t3035'
                        # 2:'MR\tNachrichtenempfänger\tX\tX\tX'
                        # 3:''
                        # len():4
                        del row_cell_texts_as_list[1]
                    index_for_middle_column = 2

                actual_edifact_struktur_cell = table.row_cells(row)[0]

                # check here for row type
                actual_row_type = define_row_type(
                    table=table,
                    edifact_struktur_cell=actual_edifact_struktur_cell,
                    text_in_row_as_list=row_cell_texts_as_list,
                )
                print(actual_row_type.name)

                if actual_row_type is row_type.HEADER:
                    continue

                elif actual_row_type is row_type.SEGMENTNAME:
                    write_segment_name_to_dataframe(
                        final_dataframe=df,
                        row_index=actual_df_row_index,
                        dataframe_row=actual_dataframe_row,
                        text_in_row_as_list=row_cell_texts_as_list,
                    )
                    actual_df_row_index = actual_df_row_index + 1
                    continue

                elif actual_row_type is row_type.SEGMENTGRUPPE:
                    write_segmentgruppe_to_dataframe(
                        final_dataframe=df,
                        row_index=actual_df_row_index,
                        dataframe_row=actual_dataframe_row,
                        text_in_row_as_list=row_cell_texts_as_list,
                    )
                    actual_df_row_index = actual_df_row_index + 1
                    continue

                elif actual_row_type is row_type.SEGMENT:
                    write_segment_to_dataframe(
                        final_dataframe=df,
                        row_index=actual_df_row_index,
                        dataframe_row=actual_dataframe_row,
                        text_in_row_as_list=row_cell_texts_as_list,
                    )
                    actual_df_row_index = actual_df_row_index + 1
                    continue

                elif actual_row_type is row_type.DATENELEMENT:
                    write_dataelement_to_dataframe(
                        final_dataframe=df,
                        row_index=actual_df_row_index,
                        dataframe_row=actual_dataframe_row,
                        text_in_row_as_list=row_cell_texts_as_list,
                        middle_cell=table.row_cells(row)[index_for_middle_column],
                    )
                    actual_df_row_index = actual_df_row_index + 1
                    continue

        df.to_csv("export.csv")
        # df.to_excel("export.xlsx")
        print(len(doc.tables[1].columns))

    except IOError:
        print("There was an error opening the file!")
        return


if __name__ == "__main__":
    main()
