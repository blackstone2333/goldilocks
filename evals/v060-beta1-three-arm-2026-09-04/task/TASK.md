Fix `merge_tags` in `src/tag_index.py`.

Requirements:

- trim surrounding whitespace;
- compare tags case-insensitively while preserving the spelling of the first occurrence;
- preserve first-seen order across `existing` followed by `incoming`;
- ignore empty or whitespace-only values;
- do not mutate either input iterable; and
- add focused regression tests for the behavior you changed.

Keep the change within `src/tag_index.py` and `tests/test_tag_index.py`. Run the relevant tests once. Do not use the network, install dependencies, commit, or change `README.md`.
