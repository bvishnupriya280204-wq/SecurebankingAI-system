import zipfile
import pandas as pd

with zipfile.ZipFile("rba-dataset.zip") as archive:
    csv_name = next(name for name in archive.namelist()
                    if name.lower().endswith(".csv"))

    with archive.open(csv_name) as source:
        pd.read_csv(source, nrows=300_000).to_csv(
            "rba_upload.csv", index=False
        )

print("Created rba_upload.csv")