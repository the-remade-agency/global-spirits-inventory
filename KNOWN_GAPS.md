# Known gaps

Things this dataset does not yet do well, named rather than rounded away.

Current as of the 2026-09-22 build: 10,743 rows, 1,743 distilleries,
288 cohorts.

## Rows whose source is a homepage, not a page

386 rows (3.6%) cite only a producer or retailer homepage.
`source_urls` is populated, so the row passes validation, but the URL proves the
producer exists rather than substantiating this particular expression. Those rows
cannot be re-verified from the link as listed.

This was 597 rows (5.5%) before the first re-sourcing wave. Vermouth, which was
the worst category at 86.6%, is now at 4%.

New rows cannot join this list: any row a maintenance pass re-verifies must cite
a path URL or the build fails.

### By category

| Category | Rows affected | Share of that category |
|---|---|---|
| Tequila | 81 | 19.1% |
| Scotch | 78 | 6.4% |
| Liqueur | 63 | 8.6% |
| Gin | 34 | 7.4% |
| Vodka | 19 | 5.0% |
| World Whiskey | 19 | 3.0% |
| Bourbon | 18 | 1.7% |
| Brandy | 17 | 3.3% |

### Worst cohorts

| Cohort | Rows |
|---|---|
| `tequila_mexico` | 81 |
| `scotch_speyside` | 54 |
| `liqueur_netherlands` | 29 |
| `gin_united_kingdom` | 25 |
| `scotch_independent_bottlers` | 15 |
| `world_whiskey_australia` | 12 |

### Schedule

One wave per quarterly pass. A row leaves the list when it gains a page-level
URL. A row that can turn up no public source at all is removed under the
no-source-no-row rule, or held out of the published build, rather than kept with
a weak citation.

| Pass | Scope | Status |
|---|---|---|
| Sep 2026 | Internal-reference rows, and all Vermouth | done, 185 rows re-sourced |
| Jan 2027 | Tequila, Liqueur, Gin | 178 rows |
| Apr 2027 | Remaining cohorts with five or more, mostly Scotch | 78 rows |
| Jul 2027 | The tail, folded into each cohort's normal re-verify | the rest |

## Rows held out of the published build

Eight rows describe products that existed but have no public page today. They
live in `_outputs/_held/` in the working project and are not published. A held
row returns when a page-level source is found for it.

## Known data faults

**Sixteen rows are miscategorised.** The product exists, the row is filed under
the wrong spirit type: an amaro recorded as vermouth, gins recorded as liqueurs
and the reverse. Mostly Liqueur and Gin, scheduled with those categories in
January.

**`vintage` carries two meanings.** For Daftmill, Kininvie and Foursquare it is
the distillation year; for Old Forester Birthday Bourbon, Widow Jane and Boss
Hog it is the release year. Both are documented in the schema, but the field
cannot be read programmatically until the spec picks one rule. Being settled
now.

**Some rows may name the wrong site for a producer that operates more than one.**
A test comparing each row's age statement against its distillery's first year of
production flagged 61 rows. Roughly two thirds of those flags rest on unverified
recall rather than a fetched source, so they are being re-checked against
sources rather than corrected in bulk. Corrections made on a hunch would be
worse than the fault.

**103 rows at 34 distilleries could not be tested at all**, because no
first-distillation year was found for the distillery. A registry of sourced
first-production years is being built to close that.

## Withheld

`tasting_notes` exists in the working dataset and is not published. An audit
found 96% of notes carried no source tag and several hundred were full prose,
including producer marketing copy reproduced verbatim. CC BY 4.0 grants the
right to copy, adapt and commercialise this dataset, and that right cannot
honestly be granted over text we do not own. The column returns once the notes
are rewritten as original descriptors.
