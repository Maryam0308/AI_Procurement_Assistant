
import argparse
import csv
import math
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient


MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "procurement_ai"
COLLECTION_NAME = "purchase_orders"
BATCH_SIZE = 1000


def parse_price(value):
    """Convert a CSV currency value into a float."""
    if value is None:
        return 0.0

    text = str(value).strip()

    if not text:
        return 0.0

    negative = text.startswith("(") and text.endswith(")")

    text = (
        text.replace("$", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )

    try:
        result = float(text)

        if not math.isfinite(result):
            raise ValueError("Non-finite price")

        return -result if negative else result

    except ValueError:
        raise ValueError(f"Invalid Total Price: {value!r}")


def parse_date(value):
    """Convert MM/DD/YYYY into a Python datetime."""
    if not value or not value.strip():
        return None

    return datetime.strptime(value.strip(), "%m/%d/%Y")


def prepare_document(row):
    """Preserve original columns and add analytics fields."""
    document = dict(row)

    document["total_price_numeric"] = parse_price(
        row.get("Total Price")
    )

    document["creation_date_parsed"] = parse_date(
        row.get("Creation Date")
    )

    return document


def import_csv(csv_path):
    path = Path(csv_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {path}"
        )

    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")

        collection = client[DATABASE_NAME][COLLECTION_NAME]

        # Never import into an existing populated collection.
        if collection.count_documents({}, limit=1) > 0:
            print("IMPORT CANCELLED.")
            print("The target collection already contains data.")
            print("No records were inserted or modified.")
            print(
                f"Database: {DATABASE_NAME}, "
                f"Collection: {COLLECTION_NAME}"
            )
            return

        print(f"Reading CSV: {path}")
        print(f"Target: {DATABASE_NAME}.{COLLECTION_NAME}")

        batch = []
        imported = 0

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            required_columns = {
                "Creation Date",
                "Total Price",
                "Purchase Order Number",
                "Department Name",
                "Supplier Name",
                "Item Name",
            }

            available_columns = set(reader.fieldnames or [])
            missing = required_columns - available_columns

            if missing:
                raise ValueError(
                    "Missing required CSV columns: "
                    + ", ".join(sorted(missing))
                )

            for row_number, row in enumerate(reader, start=2):
                try:
                    document = prepare_document(row)
                except ValueError as error:
                    raise ValueError(
                        f"CSV row {row_number}: {error}"
                    ) from error

                batch.append(document)

                if len(batch) >= BATCH_SIZE:
                    collection.insert_many(batch)
                    imported += len(batch)
                    batch.clear()

                    if imported % 10000 == 0:
                        print(f"Imported {imported:,} records")

            if batch:
                collection.insert_many(batch)
                imported += len(batch)

        print()
        print("IMPORT COMPLETED SUCCESSFULLY")
        print(f"Total imported: {imported:,}")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import California procurement CSV into MongoDB"
    )

    parser.add_argument(
        "csv_path",
        help="Path to the original procurement CSV file"
    )

    args = parser.parse_args()

    import_csv(args.csv_path)
