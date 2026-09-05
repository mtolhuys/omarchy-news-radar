# Reviewed discoveries

Each JSON file is one durable, source-linked workflow suggestion. Its canonical URL is `https://mtolhuijs.nl/news-radar/discover/<id>/`. IDs do not change when copy is corrected. Keep the original source links and review date accurate; do not imply testing or compatibility from a README review. The initial records were checked against their authors' public documentation on 5 September 2026.

Records use the collection shape in `radar/insights.py`: `id`, `title`, `summary`, `body`, `projectIds`, `source`, `sourceLinks` (optional), `shareUrl`, `reviewedAt`, and an optional strictly allowlisted `image`. All copy is plain text. Separate paragraphs with two newlines; no HTML, Markdown renderer, commands to execute, affiliate links, popularity ranking, or security endorsements.

Production uses only records whose review date has arrived and whose projects remain present in the validated catalog. Historical fixed-clock builds omit later records. A discovery creates no news event and does not enter the finite briefing by itself. Follow, mute, enabled-project matching and reading history are entirely local. Adding release-note coverage requires an explicit reviewed entry in `RELEASE_REPOSITORIES` in `radar/insights_builder.py`; a discovery never authorizes arbitrary producer requests.
