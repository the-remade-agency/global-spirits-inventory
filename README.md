# Global Spirits Inventory

A structured, openly licensed reference dataset of spirits by type and country,
compiled from producer and retailer sources on the public web.

**10,743 expressions · 1,743 distilleries · 21 spirit types · 288 cohorts**

Every row carries where it came from and when it was last checked. `source_urls`
and `last_verified` are populated on 100% of rows.

For 96.4% of rows the listed URL points at the page that substantiates
the entry, so it can be re-verified directly. The remaining 386 rows (3.6%) cite
only a producer or retailer homepage, which proves the producer exists but not
the specific expression. Those are listed in [`KNOWN_GAPS.md`](KNOWN_GAPS.md) and
are being re-sourced on the quarterly passes through to July 2027. We would
rather name that than round it up to 100%.

## Get the data

| File | What it is |
|---|---|
| [`data/spirits_inventory.csv`](data/spirits_inventory.csv) | everything in one file, 10,743 rows. Start here. |
| [`data/by_cohort/`](data/by_cohort) | the same rows split into 288 files by spirit type and region |
| [`data/manifest.json`](data/manifest.json) | build date, row counts per cohort, SHA-256 of the consolidated file |

Both views are generated from one source by `scripts/package.py`, so they cannot
disagree. The consolidated file is ~4MB and opens in Excel or Google Sheets
without complaint.

Prefer a **[tagged release](../../releases)** over the tip of `main` if you are
citing this. Releases are versioned by quarter (`v2026.10`, `v2027.01`), so a
citation points at data that does not move under you.

## Schema

10,743 rows, 21 columns.

| Column | Notes |
|---|---|
| `spirit_type` | Category name, one of 21 fixed values, e.g. `Bourbon`, `Scotch`, `Armagnac`. |
| `distillery` | The distillery that made the liquid, suffixes stripped. On third-party releases this is the **source** distillery, not the brand; `Undisclosed (<region>)` where the producer does not name it. |
| `distillery_location` | Where it was distilled, `City, State` or `City, Country`. Not corporate HQ. |
| `spirit_name` | Brand line only, e.g. `Elijah Craig`. |
| `producer_type` | Origin of the liquid: `own_make`, `sourced` (bought from another distillery), `blended` (own plus sourced stock), `unknown`. |
| `producer_brand` | The brand owner when it differs from the distillery (third-party releases). `NULL` for a distillery's own house brand. |
| `is_ndp` | Non-distiller producer. Derived: `TRUE` when `producer_brand` is set, `FALSE` when it is not, `NULL` when `producer_type` is `unknown`. |
| `is_template` | `TRUE` when the row stands for a producer programme with per-bottle variation (single-barrel, private-selection programmes). `proof`, `abv`, `batch_lot` and `vintage` are normally `NULL` on these rows because they vary by bottle. Retailer and store picks are not in the dataset. |
| `special_designation` | Semicolon-separated: the category's legal class or style (`Kentucky Straight Bourbon`, `Mezcal Artesanal`, `Bas-Armagnac`), then qualifiers (age tier, grape or agave, finish), then any named release. |
| `age_statement` | `X Years` if stated, `NAS` if the label carries no age statement, `NULL` if unknown. |
| `vintage` | Year on the label: release year for dated annual releases, distillation year for vintage Cognac, Armagnac, Calvados and single casks. `NULL` for multi-year blends and solera. |
| `batch_lot` | Producer's batch or release identifier, verbatim. |
| `proof` | US proof (2 × ABV). |
| `abv` | Alcohol by volume, one decimal. |
| `mash_bill` | What the spirit was made from, in **every** category: grains with percentages where disclosed (`wheated` / `high-rye` where not), agave species, sugarcane base, grape or fruit variety, base material of a gin or vodka. `NULL` if the producer does not disclose it; never inferred from the category's legal definition. |
| `barrel_type` | Primary maturation cask. |
| `cask_finish` | Secondary maturation cask. `NULL` means none **or** unknown, not confirmed absent. |
| `source_urls` | Semicolon-separated URLs substantiating the row. Never null. |
| `last_verified` | ISO date the row was last confirmed against its sources. |
| `label_image_url` | Link to a bottle or label image hosted elsewhere: producer page first, then aggregator, then retailer. `NULL` rather than a stock placeholder. |
| `cohort` | Spirit type plus region or producer group, e.g. `bourbon_kentucky_craft`. Added at packaging time from the source filename; matches the file name in `data/by_cohort/`. |

`cohort` is added at packaging time. In the working project the grouping lived
only in the filename, which meant a naive merge would lose the distinction
between, say, `bourbon_kentucky_craft` and `bourbon_indiana`.

## Coverage and completeness

Completeness varies by field, and the dataset does not pretend otherwise:

| Field | Populated |
|---|---|
| `source_urls` | 100.0% |
| `last_verified` | 99.98% |
| `abv` | 78.6% |
| `proof` | 77.7% |
| `age_statement` | 59.0% |
| `label_image_url` | 47.6% |
| `mash_bill` | 38.3% |

A blank is a blank. Where a value could not be sourced it is empty or `NULL`
rather than inferred. Rows flagged `is_template` normally carry nulls in
`proof`, `abv`, `batch_lot` and `vintage` because those vary bottle to bottle,
though a small number are populated where a programme defines them.

## Provenance, and why there are no tasting notes

Everything published here is factual: distillery, location, strength, recipe,
cask, age, and where each of those came from. Facts are not subject to
copyright, so this release can be licensed openly without qualification.

**Tasting notes are deliberately withheld.** The working dataset holds 5,744 of
them, and an audit before first publication found that 96% carried no source tag
and several hundred were full prose, including producer marketing copy reproduced
verbatim. CC BY 4.0 grants you the right to copy, adapt and commercialise this
dataset, and that right cannot honestly be granted over text we do not own. The
column returns once those notes have been rewritten as original descriptors.

`label_image_url` is a reference to an image hosted elsewhere. No images are
redistributed here.

## This will contain errors

10,743 rows compiled from the public web will include mistakes: renamed
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

> Pace, E. Global Spirits Inventory. The Remade Agency. CC BY 4.0.
> https://github.com/the-remade-agency/global-spirits-inventory

GitHub's **Cite this repository** button on the sidebar generates that for you,
in APA or BibTeX, from [`CITATION.cff`](CITATION.cff).

## Rebuilding

```bash
python3 scripts/package.py --src /path/to/inventory_research/_outputs
```

The script refuses to build if any source file's schema does not match the rest,
rather than quietly writing a ragged CSV.
