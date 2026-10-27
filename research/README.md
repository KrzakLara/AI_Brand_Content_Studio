# Research data and provenance

Every source and evidence item carries an `origin`:

| origin | meaning |
|---|---|
| `live` | fetched by the studio's runtime tools over real HTTP (gymbeam.hr), robots.txt respected |
| `manual_import` | collected by a person/operator outside the runtime and imported with a provenance block |
| `fixture` | recorded/synthetic test data; appears only in tests, never in `research/gymbeam_hr/` |
| `mock` | Phase 1 placeholder data |

`imports/instagram_gymbeamhr.yaml` - 10 brand-owned @gymbeamhr posts collected at development time by the
operator session (Claude Code) through the Apify MCP connector, **not** by the runtime agent.
`imports/packaging_observations_gymbeam_hr.yaml` - operator-attested visual observations of downloaded
product images (old vs new pouch), linked to image sha256 and stored as `manual`, never `verified`.

Third-party images are stored only under `runs/` (git-ignored) for analysis and are not redistributed.
