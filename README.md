# Global Spirits Inventory

A structured, openly licensed reference dataset of spirits by type and country,
compiled from producer and retailer sources on the public web.

**10,860 expressions · 1,748 distilleries · 21 spirit types · 290 cohorts**

Every row carries where it came from and when it was last checked. That is the
part that matters: `source_urls` and `last_verified` are populated on 100% of
rows, so any entry can be traced back and re-verified rather than taken on trust.

## Get the data

| File | What it is |
|---|---|
| [`data/spirits_inventory.csv`](data/spirits_inventory.csv) | everything in one file, 10,860 rows. Start here. |
| [`data/by_cohort/`](data/by_cohort) | the same rows split into 290 files by spirit type and region |
| [`data/manifest.json`](data/manifest.json) | build date, row counts per cohort, SHA-256 of the consolidated file |

Both views are generated from one source by `scripts/package.py`, so they cannot
disagree. The consolidated file is ~4MB and opens in Excel or Google Sheets
without complaint.

Prefer a **[tagged release](../../releases)** over the tip of `main` if you are
citing this. Releases are versioned by quarter (`v2026.10`, `v2027.01`), so a
citation points at data that does not move under you.

## Schema

10,860 rows, 22 columns.

| Column | Notes |
|---|---|
| `spirit_type` |  |
| `distillery` |  |
| `distillery_location` |  |
| `spirit_name` |  |
| `producer_type` |  |
| `producer_brand` |  |
| `is_ndp` |  |
| `is_template` |  |
| `special_designation` |  |
| `age_statement` |  |
| `vintage` |  |
| `batch_lot` |  |
| `proof` |  |
| `abv` |  |
| `mash_bill` |  |
| `barrel_type` |  |
| `cask_finish` |  |
| `tasting_notes` |  |
| `source_urls` |  |
| `last_verified` |  |
| `label_image_url` |  |
| `cohort` |  |

`cohort` is added at packaging time. In the working project the grouping lived
only in the filename, which meant a naive merge would lose the distinction
between, say, `bourbon_kentucky_craft` and `bourbon_indiana`.

## Coverage and completeness

Completeness varies by field, and the dataset does not pretend otherwise:

| Field | Populated |
|---|---|
| `source_urls` | 100.0% |
| `last_verified` | 100.0% |
| `abv` | 78.6% |
| `proof` | 77.7% |
| `age_statement` | 58.9% |
| `tasting_notes` | 52.9% |
| `label_image_url` | 47.3% |
| `mash_bill` | 38.5% |

A blank is a blank. Where a value could not be sourced it is empty or `NULL`
rather than inferred.

## Provenance, and a word on tasting notes

`tasting_notes` entries tagged `[brand]` are derived from producer-published
descriptions and are attributed as such in the field itself. Factual attributes
(distillery, proof, ABV, mash bill, age statement) are not subject to copyright.
`label_image_url` is a reference to an image hosted elsewhere; no images are
redistributed here.

## This will contain errors

10,860 rows compiled from the public web will include mistakes: renamed
expressions, discontinued lines, transcription errors, sources that have since
moved. That is the nature of the exercise, not an excuse.

**Corrections are welcome and are the reason this is public.** Open an issue, or
send a pull request against the file in `data/by_cohort/` — that is the canonical
place to fix a row. Please include the source URL supporting the change.

## Maintenance

Refreshed quarterly. Each pass re-runs collection, updates `last_verified`, and
is published as a tagged release. First scheduled pass: **October 2026**.

## Licence

[CC BY 4.0](LICENSE). Use it, change it, build on it, sell things with it. The
one condition is attribution:

> Global Spirits Inventory, The Remade Agency, CC BY 4.0.
> https://github.com/the-remade-agency/global-spirits-inventory

## Rebuilding

```bash
python3 scripts/package.py --src /path/to/inventory_research/_outputs
```

The script refuses to build if any source file's schema does not match the rest,
rather than quietly writing a ragged CSV.
