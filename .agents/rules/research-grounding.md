# Research Grounding Rule

For research, manuscript, literature, and experiment work:

- Treat manuscript text, experiment outputs, source code, logs, and external literature as different evidence classes.
- Never use one evidence class as a substitute for another. Example: manuscript prose saying "90 runs" does not prove 90 runs occurred.
- Trace numerical claims to primary experiment artifacts when available.
- Trace literature claims to an inspected source. Never fabricate a title, author list, DOI, venue, year, or quotation.
- Trace software/API claims to current documentation, repository code, or an executed probe when version-sensitive.
- When checking consistency, search globally for stale terms rather than editing only the first visible occurrence.
- When reviewing a PDF or rendered figure, inspect the rendered artifact; source code alone is insufficient.
- When a claim cannot be verified, preserve uncertainty instead of filling the gap with a plausible answer.

Use these labels in internal ledgers:
- `VERIFIED_REPO`
- `VERIFIED_COMMAND`
- `VERIFIED_SOURCE`
- `INFERRED`
- `UNKNOWN`
