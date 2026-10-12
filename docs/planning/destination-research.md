# Demo destination source checks — 13 October 2026

These are historical listings for the demo area, not evidence of current opening, road access, capacity or safety. Do not describe a route or site as safe. Coordinate attribution and flood designation attribution are separate facts. Zhao Wei can replace or supplement these references with more recent official notices.

## Pasar Moden Sri Muda — parking candidate

- The [Ministry of Housing and Local Government MyWC listing](https://mywc.kpkt.gov.my/toilet/pasar-moden-sri-muda-seksyen-25) names Pasar Moden Sri Muda Seksyen 25 under MBSA. Its public map source gives latitude `3.0314414`, longitude `101.5356055`. This identifies the facility, not the parking entrance or a particular floor.
- [Bernama reporting reproduced by Astro Awani, 9 November 2022](https://www.astroawani.com/berita-malaysia/persediaan-banjir-parkir-bertingkat-di-pasar-moden-sri-muda-dibuka-390371) reports the multistorey parking was opened during that flood preparation, quoting the Shah Alam police chief's statement. [Awani's 8 November report](https://www.astroawani.com/berita-malaysia/banjir-kilat-penduduk-taman-sri-muda-dinasihat-letak-kenderaan-di-kawasan-tinggi-390318) attributes opening to an MBSA statement. The original council social post has not yet been directly retrieved; treat these as attributed reporting, not a fresh council confirmation.
- Suitable wording: “Previously designated parking (2022); check that it is open.” No current-open claim. No source inspected establishes a minimum parking floor: `min_level` must remain unknown rather than copying the spec's illustrative “2+”. Use an explicit unknown-floor fallback unless later verified.

## Dewan Kenanga, Seksyen 28 — evacuation candidate

- [NADMA's 12 April 2025 article](https://www.nadma.gov.my/bi/media-en/news/3850-satu-pps-lebih-kapasiti-dua-hampir-penuh) records use of Dewan Kenanga, Seksyen 28 as a PPS. It also names Dewan Azalea (Seksyen 25) and Dewan Bakawali (Seksyen 36), but those coordinates have not been checked here.
- [Selangor State Assembly hall listing](https://dewan.selangor.gov.my/question/dewan-orang-ramai-dan-balai-raya/) gives Dewan Kenanga's address as Jalan Dengkil 28/21, Section 28.
- [Waze's facility listing](https://www.waze.com/live-map/directions/my/selangor/shah-alam/mbsa-council-section-28-%28kenanga-hall%29?to=place.ChIJJ8t8tvqyzTERiGcT6545ctQ) matches that name/address; its public structured page data gives `3.0051556, 101.560237`. These are map-provider coordinates, not government survey coordinates or an entrance guarantee.
- Suitable wording: “Listed evacuation centre; current opening unconfirmed.” Historical official listing is confirmed, current opening remains unknown. The `verified` field must mean historical source verification explicitly, never current safety/open status.

## Implementation constraints

Keep source URLs, historical date, coordinate source and opening status with each seed. Never invent a current-open timestamp, exact entrance, minimum level or local contact. Render a no-destination fallback when no eligible sourced point exists. A synthetic demo label does not justify presenting fabricated real-world destinations as verified. Cloud/deployed acceptance and field checks remain separate.
