# Known gaps

Things this dataset does not yet do well, named rather than rounded away.

## Rows whose source is a homepage, not a page

597 rows (5.5% of 10,768) cite only a producer or retailer
homepage. `source_urls` is populated, so the row passes validation, but the URL
proves the producer exists rather than substantiating this particular
expression. They cannot be re-verified from the link as listed.

New rows cannot join this list: any row a maintenance pass re-verifies must cite
a path URL or the build fails.

### By category

| Category | Rows affected | Share of that category |
|---|---|---|
| Liqueur | 141 | 19.0% |
| Vermouth | 116 | 86.6% |
| Tequila | 82 | 19.4% |
| Scotch | 78 | 6.4% |
| Gin | 53 | 11.5% |
| Bourbon | 20 | 1.9% |
| Vodka | 19 | 5.0% |
| World Whiskey | 19 | 3.0% |
| Brandy | 17 | 3.3% |
| Irish Whiskey | 15 | 2.5% |

### Worst cohorts

| Cohort | Rows |
|---|---|
| `tequila_mexico` | 82 |
| `scotch_speyside` | 54 |
| `vermouth_italy` | 50 |
| `gin_united_kingdom` | 33 |
| `liqueur_netherlands` | 30 |
| `liqueur_united_states` | 30 |
| `vermouth_spain` | 27 |
| `scotch_independent_bottlers` | 15 |

### Schedule

One wave per quarterly pass. A row leaves the list when it gains a page-level
URL. A row that can turn up no public source at all is removed under the
no-source-no-row rule, rather than kept with a weak citation.

| Pass | Scope | Rows |
|---|---|---|
| Oct 2026 | Internal-reference rows, and all Vermouth | 227 |
| Jan 2027 | Tequila, Liqueur, Gin | 167 |
| Apr 2027 | Remaining cohorts with five or more, mostly Scotch | 143 |
| Jul 2027 | The tail, folded into each cohort's normal re-verify | 60 |

## Known data faults

- **Bulleit 12 Year Old is marked `own_make`.** Bulleit's Shelbyville distillery
  opened in 2017, so a twelve-year-old expression cannot be its own distillate.
  The seven-year Bonded is plausible and is left alone.
- **43 rows in `bourbon_ndps_bottlers`** name a disclosed source distillery, so
  the ownership rule places them in a geography cohort instead. A routing
  question, not duplication; no row appears twice.
- **A.H. Hirsch** was distilled at Pennco in Pennsylvania and belongs in
  `bourbon_other_states` rather than a Kentucky cohort.
- **Long Pond ITP-15**, distilled 2006, may belong in `rum_legacy_closed`
  depending on that distillery's closure and reopening dates.

## Withheld

`tasting_notes` exists in the working dataset and is not published. An audit
found 96% of notes carried no source tag and several hundred were full prose,
including producer marketing copy reproduced verbatim. CC BY 4.0 grants the
right to copy, adapt and commercialise this dataset, and that right cannot
honestly be granted over text we do not own. The column returns once the notes
are rewritten as original descriptors.
