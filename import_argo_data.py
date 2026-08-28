import asyncio
from pathlib import Path

import pandas as pd
from geoalchemy2 import WKTElement
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.float import Float
from app.models.profile import Profile
from app.models.measurement import Measurement
from app.models.bgc_measurement import BGCMeasurement


EXCEL_FILE = Path("argo_20_global_demo_extended.xlsx")


async def import_data():
    # ---------------------------------------------------------
    # 1. Check that the Excel file exists
    # ---------------------------------------------------------
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {EXCEL_FILE.resolve()}"
        )

    print(f"Reading dataset: {EXCEL_FILE}")

    # ---------------------------------------------------------
    # 2. Read Excel data
    # ---------------------------------------------------------
    df = pd.read_excel(EXCEL_FILE, sheet_name="ARGO_Data")

    print(f"Rows found: {len(df)}")
    print(f"Unique floats: {df['float_id'].nunique()}")

    # ---------------------------------------------------------
    # 3. Validate required columns
    # ---------------------------------------------------------
    required_columns = [
        "float_id",
        "region",
        "latitude",
        "longitude",
        "date",
        "pressure_dbar",
        "depth_m",
        "temperature_C",
        "salinity",
        "density_kg_m3",
        "dissolved_oxygen_umol_kg",
        "oxygen_saturation_pct",
        "chlorophyll_mg_m3",
        "nitrate_umol_kg",
        "pH",
        "PAR_umol_m2_s",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    # ---------------------------------------------------------
    # 4. Connect to PostgreSQL
    # ---------------------------------------------------------
    print("Connecting to PostgreSQL...")

    async with AsyncSessionLocal() as session:

        # -----------------------------------------------------
        # 5. Safety check - don't accidentally duplicate data
        # -----------------------------------------------------
        existing_floats = (
            await session.execute(
                select(Float).limit(1)
            )
        ).scalar_one_or_none()

        if existing_floats is not None:
            raise RuntimeError(
                "The floats table already contains data. "
                "Import cancelled to prevent duplicate records."
            )

        print("Database is empty. Starting import...")

        # -----------------------------------------------------
        # 6. Create Float records
        # -----------------------------------------------------
        float_rows = (
            df[
                ["float_id", "region"]
            ]
            .drop_duplicates()
            .sort_values("float_id")
        )

        floats = []

        for _, row in float_rows.iterrows():
            float_obj = Float(
                id=str(row["float_id"]),
                region=str(row["region"]),
            )

            floats.append(float_obj)

        session.add_all(floats)

        print(f"Prepared {len(floats)} float records.")

        # -----------------------------------------------------
        # 7. Create Profile records
        # -----------------------------------------------------
        profiles = []

        profile_groups = df.groupby(
            ["float_id", "date", "latitude", "longitude"],
            sort=True,
        )

        for profile_id, ((float_id, profile_date, latitude, longitude), _) in enumerate(
            profile_groups,
            start=1,
        ):
            profile = Profile(
                id=profile_id,
                float_id=str(float_id),
                cycle_number=1,
                date=pd.Timestamp(profile_date).date(),
                latitude=float(latitude),
                longitude=float(longitude),
                geom=WKTElement(
                    f"POINT({float(longitude)} {float(latitude)})",
                    srid=4326,
                ),
            )

            profiles.append(profile)

        session.add_all(profiles)

        print(f"Prepared {len(profiles)} profile records.")

        # Flush so generated/assigned IDs are available
        await session.flush()

        # -----------------------------------------------------
        # 8. Map each Excel row to its Profile
        # -----------------------------------------------------
        profile_lookup = {}

        for profile in profiles:
            key = (
                profile.float_id,
                profile.date,
                round(profile.latitude, 6),
                round(profile.longitude, 6),
            )
            profile_lookup[key] = profile

        # -----------------------------------------------------
        # 9. Create Measurement + BGCMeasurement records
        # -----------------------------------------------------
        measurements = []
        bgc_records = []

        for _, row in df.iterrows():

            profile_date = pd.Timestamp(row["date"]).date()

            key = (
                str(row["float_id"]),
                profile_date,
                round(float(row["latitude"]), 6),
                round(float(row["longitude"]), 6),
            )

            profile = profile_lookup[key]

            measurement = Measurement(
                profile=profile,
                pressure_dbar=float(row["pressure_dbar"]),
                depth_m=float(row["depth_m"]),
                temperature_c=float(row["temperature_C"]),
                salinity=float(row["salinity"]),
                density_kg_m3=float(row["density_kg_m3"]),
            )

            measurements.append(measurement)

        session.add_all(measurements)

        # Flush so measurement IDs exist
        await session.flush()

        print(f"Prepared {len(measurements)} measurement records.")

        # -----------------------------------------------------
        # 10. Create BGC records
        # -----------------------------------------------------
        for excel_row, measurement in zip(
            df.itertuples(index=False),
            measurements,
        ):
            bgc = BGCMeasurement(
                measurement_id=measurement.id,
                profile_id=measurement.profile_id,

                dissolved_oxygen_umol_kg=float(
                    excel_row.dissolved_oxygen_umol_kg
                ),
                oxygen_saturation_pct=float(
                    excel_row.oxygen_saturation_pct
                ),
                chlorophyll_mg_m3=float(
                    excel_row.chlorophyll_mg_m3
                ),
                nitrate_umol_kg=float(
                    excel_row.nitrate_umol_kg
                ),
                ph=float(
                    excel_row.pH
                ),
                par_umol_m2_s=float(
                    excel_row.PAR_umol_m2_s
                ),
            )

            bgc_records.append(bgc)

        session.add_all(bgc_records)

        print(f"Prepared {len(bgc_records)} BGC records.")

        # -----------------------------------------------------
        # 11. Commit everything in one transaction
        # -----------------------------------------------------
        await session.commit()

        print()
        print("=" * 60)
        print("ARGO DATA IMPORT SUCCESSFUL")
        print("=" * 60)
        print(f"Floats:        {len(floats)}")
        print(f"Profiles:      {len(profiles)}")
        print(f"Measurements:  {len(measurements)}")
        print(f"BGC records:   {len(bgc_records)}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(import_data())