import openpyxl
from collections import defaultdict

wb = openpyxl.load_workbook("argo_20_global_demo_extended.xlsx", data_only=True)
sheet = wb["ARGO_Data"]
rows = list(sheet.iter_rows(values_only=True))
headers = rows[0]
data = [dict(zip(headers, r)) for r in rows[1:]]

floats = defaultdict(list)
for d in data:
    floats[d["float_id"]].append(d)

print(f"Total Floats: {len(floats)}")
for fid, records in floats.items():
    dates = set(r["date"] for r in records)
    coords = set((r["latitude"], r["longitude"]) for r in records)
    regions = set(r["region"] for r in records)
    pressures = [r["pressure_dbar"] for r in records]
    print(f"Float {fid}: {len(records)} levels, regions={regions}, dates={dates}, coords={coords}, pressures={pressures}")
