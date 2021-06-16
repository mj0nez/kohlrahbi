import re
from pathlib import Path

import pandas as pd


def beautify_bedingungen(bedingung: str) -> str:
    """Inserts newline characters before each Bedingung key [###]

        Example:
        [12] Wenn SG4
    DTM+471 (Ende zum
    nächstmöglichem
    Termin) nicht vorhanden

    [13] Wenn SG4
    STS+E01++Z01 (Status
    der Antwort: Zustimmung
    mit Terminänderung)
    nicht vorhanden

    ->

    [12] Wenn SG4 DTM+471 (Ende zum nächstmöglichem Termin) nicht vorhanden
    [13] Wenn SG4 STS+E01++Z01 (Status der Antwort: Zustimmung mit Terminänderung) nicht vorhanden

    Args:
        bedingung (str): Text in a Bedingung cell

    Returns:
        str: Beautified text with one Bedingung per line
    """

    if isinstance(bedingung, str):
        bedingung = bedingung.replace("\n", " ")
        matches = re.findall(r"\[\d*\]", bedingung)
        for match in matches[1:]:
            index = bedingung.find(match)
            bedingung = bedingung[:index] + "\n" + bedingung[index:]
    return bedingung


def export_pruefidentifikator(pruefi: str, df: pd.DataFrame, output_directory_path: Path):
    """Exports the current Prüfidentifikator in different file formats: json, csv and xlsx
    Each Prüfidentifikator is saved in an extra file.

    Args:
        pruefi (str): Current Prüfidentifikator
        df (pd.DataFrame): DataFrame which contains all information
        output_directory_path (Path): Path to the output directory
    """

    json_output_directory_path = output_directory_path / "json"
    csv_output_directory_path = output_directory_path / "csv"
    xlsx_output_directory_path = output_directory_path / "xlsx"

    json_output_directory_path.mkdir(parents=True, exist_ok=True)
    csv_output_directory_path.mkdir(parents=True, exist_ok=True)
    xlsx_output_directory_path.mkdir(parents=True, exist_ok=True)

    # write for each pruefi an extra file
    columns_to_export = list(df.columns)[:5] + [pruefi]
    columns_to_export.append("Bedingung")
    # df["Bedingung"] = df["Bedingung"].apply(beautify_bedingungen)
    df_to_export = df[columns_to_export]
    df_to_export.to_csv(csv_output_directory_path / f"{pruefi}.csv")

    # for orient in ["split", "records", "index", "columns", "values", "table"]:

    #     df_to_export.to_json(
    #         json_output_directory_path / f"{pruefi}-{orient}.json", force_ascii=False, orient=orient
    #     )
    df_to_export.to_json(json_output_directory_path / f"{pruefi}.json", force_ascii=False, orient="records")

    try:
        with pd.ExcelWriter(xlsx_output_directory_path / f"{pruefi}.xlsx", engine="xlsxwriter") as writer:
            df_to_export.to_excel(writer, sheet_name=f"{pruefi}")
            workbook = writer.book
            worksheet = writer.sheets[f"{pruefi}"]
            wrap_format = workbook.add_format({"text_wrap": True})
            column_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
            column_widths = [3.5, 47, 9, 14, 39, 33, 18, 102]
            for column_letter, column_width in zip(column_letters, column_widths):
                excel_header = f"{column_letter}:{column_letter}"
                worksheet.set_column(excel_header, column_width, wrap_format)
            print(f"💾 Saved file for Pruefidentifikator {pruefi}")
    except PermissionError:
        print(f"💥 The Excel file {pruefi}.xlsx is open. Please close this file and try again.")


def export_all_pruefidentifikatoren_in_one_file(
    pruefi: str, df: pd.DataFrame, output_directory_path: Path, file_name: str
):
    """Exports all Prüfidentifikatoren in one AHB into **one** Excel file

    Args:
        pruefi (str): Current Prüfidentifikator
        df (pd.DataFrame): DataFrame which contains all information
        output_directory_path (Path): Path to the output directory
        file_name (str): Name of the readed AHB file
    """

    xlsx_output_directory_path = output_directory_path / "xlsx"
    xlsx_output_directory_path.mkdir(parents=True, exist_ok=True)

    path_to_all_in_one_excel = xlsx_output_directory_path / f"{file_name[:-5]}.xlsx"

    # write for each pruefi an extra file
    columns_to_export = list(df.columns)[:5] + [pruefi]
    columns_to_export.append("Bedingung")
    df_to_export = df[columns_to_export]

    try:
        with pd.ExcelWriter(path=path_to_all_in_one_excel, mode="a", engine="openpyxl") as writer:
            df_to_export.to_excel(writer, sheet_name=f"{pruefi}")
    except FileNotFoundError:
        with pd.ExcelWriter(path=path_to_all_in_one_excel, mode="w", engine="openpyxl") as writer:
            df_to_export.to_excel(writer, sheet_name=f"{pruefi}")
    except PermissionError:
        print(f"💥 The Excel file {file_name[:-5]}.xlsx is open. Please close this file and try again.")