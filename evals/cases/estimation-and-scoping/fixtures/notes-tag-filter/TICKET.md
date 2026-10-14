# NOTES-142: Filter search results by tag

Acceptance criteria (agreed with product on 2026-10-09):

- `python -m notes search <text> --tag <tag>` returns only notes that match the text AND carry the tag.
- The web endpoint accepts `/search?q=<text>&tag=<tag>` with the same semantics.
- A note with no tags never matches a tag filter.
- Matching is case-insensitive for tags, like it is for text.
- One unit test covers the AND semantics.

Not decided yet: whether several `--tag` values mean AND or OR (product to confirm).

Sprint: 5 working days, starts 2026-10-15. The lead wants to know whether this fits.
