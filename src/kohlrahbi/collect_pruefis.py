from datetime import date
from pathlib import Path

import docx
import toml
from docx.table import Table

from kohlrahbi.enums import FormatPrefix
from kohlrahbi.helper.read_functions import does_the_table_contain_pruefidentifikatoren, get_all_paragraphs_and_tables
from kohlrahbi.helper.seed import Seed
from kohlrahbi.logger import logger

all_pruefis = []

for format in FormatPrefix:
    print(format)

    path_to_ahb_documents: Path = Path("/Users/kevin/workspaces/hochfrequenz/edi_energy_mirror/edi_energy_de/current")

    docx_files_in_ahb_documents: list[Path] = [
        path
        for path in path_to_ahb_documents.iterdir()
        if path.is_file()
        if path.suffix == ".docx"
        if "AHB" in path.name
        if "LesefassungmitFehlerkorrekturen" in path.name
        if format.name in path.name
    ]

    for ahb_file_path in docx_files_in_ahb_documents:

        doc = docx.Document(ahb_file_path)  # Creating word reader object.

        for item in get_all_paragraphs_and_tables(parent=doc):
            if isinstance(item, Table) and does_the_table_contain_pruefidentifikatoren(table=item):

                # check which pruefis
                seed = Seed.from_table(docx_table=item)
                logger.info("Found a table with the following pruefis: %s", seed.pruefidentifikatoren)
                all_pruefis = all_pruefis + seed.pruefidentifikatoren

all_pruefis = sorted(list(set(all_pruefis)))

toml_data = {
    "meta_data": {"updated_on": date.today()},
    "content": {"pruefidentifikatoren": all_pruefis},
}

with open(Path(__file__).parent / Path("all_known_pruefis.toml"), "w") as f:
    toml.dump(toml_data, f)