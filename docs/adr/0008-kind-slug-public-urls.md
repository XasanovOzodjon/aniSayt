# Public catalog URLs use Kind prefix plus title slug

Title pages and the player are public, bookmarkable paths, not query ids. We put Kind in the first segment (`/anime/`, `/kino/`, `/drama/`, `/serial/`) so film and drama do not share a flat slug space with `/catalog/` and `/party/`, then the Anime slug, then `episode{n}` (and `s{season}/` only when the Season is not 1). `/detail/?id=` and `/player/?episode=` redirect to those paths so old links keep working.
