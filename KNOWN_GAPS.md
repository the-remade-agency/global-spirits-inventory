# Known gaps

Things this dataset does not yet do well, named rather than rounded away.

Current as of the 2026-09-22 build: 10,743 rows, 1,734 distilleries,
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

**Ten distilleries appear under two spellings.** The `distillery` column holds
1,744 distinct strings, of which ten are capitalisation or punctuation variants
of another entry. The real count is 1,734, which is the figure quoted above and
in the README. Anyone grouping on the raw string will get 1,744 and should
normalise first.

| Spelling | Rows | Also appears as | Rows |
| --- | ---: | --- | ---: |
| `KOVAL Distillery` | 5 | `Koval Distillery` | 3 |
| `La Nina del Mezcal (CRM NOM O170X)` | 1 | `La Nina del Mezcal (CRM NOM-O170X)` | 4 |
| `Leopold Bros` | 2 | `Leopold Bros.` | 6 |
| `Los Siete Misterios (CRM NOM O153X)` | 5 | `Los Siete Misterios (CRM NOM-O153X)` | 5 |
| `Mezcalero (CRM NOM O14X)` | 6 | `Mezcalero (CRM NOM-O14X)` | 21 |
| `Never Never Distilling Co` | 1 | `Never Never Distilling Co.` | 4 |
| `Paul Marie & Fils` | 2 | `Paul-Marie & Fils` | 2 |
| `SAKURAO Distillery` | 8 | `Sakurao Distillery` | 1 |
| `St George Spirits` | 2 | `St. George Spirits` | 19 |
| `The Distillery (Phuket)` | 1 | `The Distillery Phuket` | 1 |

No row is wrong; the name is inconsistent between rows. Queued for the October
pass, where the merge also fixes the NOM formatting on the three mezcal entries.

**Sixteen rows are miscategorised.** The product exists, the row is filed under
the wrong spirit type: an amaro recorded as vermouth, gins recorded as liqueurs
and the reverse. Mostly Liqueur and Gin, scheduled with those categories in
January.

**`vintage` carries two meanings in the published data.** For Daftmill, Kininvie
and Foursquare it is the distillation year; for Old Forester Birthday Bourbon,
Widow Jane and Boss Hog it is the release year.

The collection spec now settles it: `vintage` is the year the spirit was
distilled, in every category, and a release year belongs at the front of
`batch_lot` as `2019 Release`. **The published data does not yet follow that
rule.** 515 rows are known to need re-keying and up to 506 more need checking
against their labels, against 1,498 that are already correct.

Until that pass runs, read a `vintage` in the US whiskey categories as a release
year. The schema documentation in the README describes the data as it is rather
than as the spec intends, and will change when the data does.

**Thirty rows carry an age their named distillery cannot have produced.** A test
comparing each row's age statement against its distillery's first year of
production flagged 61 rows. Of those, 31 were corrected on fetched evidence: 24
Old Forester Birthday Bourbon rows were naming a distillery that opened in 2018
for whiskey distilled between 1989 and 2013.

The other 30 are listed below with their evidence basis, and **have not been
changed**. Four rest on model recall alone. Those are leads, not findings, and
they are labelled so rather than quietly presented as facts.

| Row | Cohort | Suspected | Basis |
|---|---|---|---|
| Tullamore D.E.W. 14, 18, and 15 Year Trilogy | irish_whiskey_established | Not distilled at Tullamore; own production from 2014, brand made at Midleton before | fetched + arithmetic |
| Dunville's VR 20 and 21 Year | irish_whiskey_new_craft | Sourced; Echlinville first filled casks 5 Aug 2013 | fetched + arithmetic |
| WhistlePig 12, 15, 18 Year, Boss Hog VII and VIII | rye_other_states | Sourced; farm production began 2015, aged stock outsourced | fetched + arithmetic |
| St Nicholas Abbey 18, 20, 25 Year | rum_barbados | Foursquare-distilled stock | fetched, sourcing |
| Fenwicks 4 and 5 Year (×3) | american_whiskey_indiana, bourbon_indiana | Sourced; distillery opened 2023 | fetched + arithmetic |
| Milam & Greene Castle Hill 15 Year | bourbon_other_states | Distilled in Tennessee, filled 18 Jul 2007 | fetched, sourcing |
| Milam & Greene Castle Hill 13 Year | bourbon_other_states | Same series, likely same source | **recall, unverified** |
| Widow Jane The Vaults 15 and Black Opal 20 | bourbon_other_states | Sourced from undisclosed distilleries | fetched, sourcing |
| Uncle Nearest 1856 and 1820 11 Year | tennessee_whiskey | Sourced; label says bottled at, not distilled at | fetched, sourcing / opening date |
| Boxergrail Founder's 8 Year Rye | rye_kentucky | Rabbit Hole's distillery opened 2018 | fetched, opening date |
| Bull Run Pinot Noir Finished 17 Year | american_whiskey_other_states | Distillery started 2010 | fetched + arithmetic |
| Lancaster 7 Year Porter Cask | american_single_malt_northeast_mid_atlantic | Sourced; federal permit 2021 | fetched + arithmetic |
| The First Millionaire 4 Year | american_single_malt_california | Calistoga Depot opened Apr 2024 | fetched, opening date |
| Old Hamer 10 Year | bourbon_indiana | Sourced; West Fork's opening year unconfirmed | **recall, unverified** |
| Pierre Ferrand Abel 45 Year | cognac_france | Probably a false positive; flag used an ownership change, not a distillation date | **recall, unverified** |
| Tipperary Homegrown 8 Year | irish_whiskey_new_craft | May predate the farm distillery | **recall, unverified** |
| Bimber Apogee XII 12 Year | world_whiskey_england | Arithmetically impossible, see below | fetched + arithmetic |

**Bimber Apogee XII is the firmest of these.** Bimber laid its first casks on 26
May 2016, so a twelve-year-old Bimber distillate cannot exist before 2028. The
producer's own page describes it as a blended malt of Highland and Speyside
whiskies finished in Bimber casks. The row's `own_make` and its distillery are
both wrong, and as a Scotch-origin blended malt it is also in the wrong cohort.

**One correction rests on a weaker source than the rest.** The 24 Old Forester
rows depend on Old Forester production having moved to the Shively plant in
1979, and the only page found for that date is an enthusiast site. Thirteen rows
(the 2002 to 2015 releases) rest on it; the 2004-and-later releases have a
producer press release. The correction was kept because the previous value named
a distillery that did not exist when the whiskey was made, which is wrong on
arithmetic rather than on sourcing. A weakly sourced right answer beats a
well-formatted wrong one.

**Also open:** other Parker's Heritage rows still name Bernheim although some
predate Heaven Hill's 1999 acquisition of it, and two `rye_kentucky` rows give
Brown-Forman Distillery's location as Louisville rather than Shively.

**103 rows at 34 distilleries could not be tested at all**, because no
first-distillation year was found. A registry of sourced first-production years
now covers 46 distilleries, each with a fetched page, and grows each pass.

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
