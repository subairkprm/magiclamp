# Documentation

MagicLamp's documentation follows the [Diátaxis](https://diataxis.fr/) framework.
Each section has a different *purpose*, so you should pick the one that matches
what you are trying to do right now:

| Section | Purpose | Read this if you want to… |
|---|---|---|
| **[Tutorials](tutorials/)**       | Learning-oriented   | Get the system running for the first time |
| **[How-To Guides](how-to/)**      | Task-oriented       | Achieve a specific outcome (deploy, configure) |
| **[Reference](reference/)**       | Information-oriented| Look up an exact API, schema, or config flag |
| **[Explanation](explanation/)**   | Understanding-oriented | Build a mental model of how the Brain works |
| **[ADR](adr/)**                   | Architecture record | See *why* a structural decision was made |

Existing documents are being migrated into this structure (see
`adr/0001-brain-router-split.md`). The pre-existing `rag.md` lives at
`docs/rag.md` until it is moved into `explanation/rag.md`.

For changes by version, see [`CHANGELOG.md`](../CHANGELOG.md). For breaking
changes & upgrade notes, see [`MIGRATION.md`](../MIGRATION.md).
