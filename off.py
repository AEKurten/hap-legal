"""Open Food Facts products sold in South Africa as catalog rows, one JSON
object per line.

    python3 -I tool/catalog/off.py products.csv.gz > off.jsonl

Takes the CSV export from https://world.openfoodfacts.org/data
(en.openfoodfacts.org.products.csv.gz, tab-separated, about 1.5 GB). The
data is under the Open Database Licence. Choices match
OpenFoodFactsClient.parseHit in the app: a missing value stays null, and
energy over 910 kcal per 100 g is kept so the app can say why it set it
aside.
"""

import gzip
import json
import re
import sys

LOCAL = "en:south-africa"
KJ_PER_KCAL = 4.184
VOLUME = re.compile(r"\d\s*(ml|cl|dl|l)\b", re.IGNORECASE)


def number(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value >= 0 else None


def main(path):
    rows = {}
    seen = mismatched = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\n").split("\t")
        col = {name: i for i, name in enumerate(header)}

        def get(cols, name):
            i = col.get(name)
            return cols[i].strip() if i is not None and i < len(cols) else ""

        for line in f:
            # Cheap test first: most of the 4 million products aren't local.
            if LOCAL not in line:
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) != len(header):
                mismatched += 1
                continue
            if LOCAL not in get(cols, "countries_tags").split(","):
                continue
            seen += 1
            code = get(cols, "code")
            name = get(cols, "product_name") or get(cols, "generic_name")
            # Without a name the product can't be recognised in a list.
            if not code or not name:
                continue
            pack_size = get(cols, "quantity") or None
            kj = number(get(cols, "energy-kj_100g")) or number(
                get(cols, "energy_100g")
            )
            kcal = number(get(cols, "energy-kcal_100g"))
            if kcal is None and kj is not None:
                kcal = round(kj / KJ_PER_KCAL, 1)
            sodium_g = number(get(cols, "sodium_100g"))
            rows[code] = {
                "source": "openFoodFacts",
                "source_ref": code,
                "name": name[:300],
                "brand": (get(cols, "brands").split(",")[0].strip() or None),
                "pack_size": pack_size,
                # Liquids' "_100g" values are per 100 ml.
                "basis": "per100ml"
                if pack_size and VOLUME.search(pack_size)
                else "per100g",
                "energy_kcal": kcal,
                "protein_g": number(get(cols, "proteins_100g")),
                "carbs_g": number(get(cols, "carbohydrates_100g")),
                "fat_g": number(get(cols, "fat_100g")),
                "fiber_g": number(get(cols, "fiber_100g")),
                "sugars_g": number(get(cols, "sugars_100g")),
                "saturated_fat_g": number(get(cols, "saturated-fat_100g")),
                "sodium_mg": None if sodium_g is None else round(sodium_g * 1000, 1),
                "is_local": True,
                "popularity": number(get(cols, "unique_scans_n")) or 0,
            }
    for r in rows.values():
        print(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
    print(
        f"{seen} South African products, {len(rows)} with a name and barcode, "
        f"{mismatched} malformed lines skipped",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1])
