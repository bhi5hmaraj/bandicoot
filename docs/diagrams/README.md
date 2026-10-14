# Diagrams

Graphviz sources (`.dot`) and rendered SVGs. Edit the `.dot` file, then render it again and commit both files.

| Diagram | Shows | Used in |
|---|---|---|
| [rmab-workflow](rmab-workflow.svg) | How Bandicoot turns a contact budget into a ranked list | [README](../../README.md) |
| [problem-modeling](problem-modeling.svg) | How a program maps to an RMAB | [RMAB fundamentals](../rmab-fundamentals.md) |
| [state-model](state-model.svg) | The 2-state model for one participant, with example indices | [RMAB fundamentals](../rmab-fundamentals.md) |
| [system-architecture](system-architecture.svg) | Built and planned components | [README](../../README.md), [architecture](../architecture.md) |
| [training-pipeline](training-pipeline.svg) | The planned weekly training job | [architecture](../architecture.md) |
| [recommendation-flow](recommendation-flow.svg) | What `POST /api/v1/recommend` does | [architecture](../architecture.md) |
| [vaccination-use-case](vaccination-use-case.svg) | The reference use case | [vaccination use case](../use-cases/vaccination.md) |

## Render

Install Graphviz (`apt install graphviz` or `brew install graphviz`). Then run:

```bash
cd docs/diagrams
for file in *.dot; do dot -Tsvg "$file" -o "${file%.dot}.svg"; done
```

## Style rules

All diagrams use the same style. Copy the `graph`, `node`, and `edge` blocks from an existing file.

| Color | Fill | Border | Meaning |
|---|---|---|---|
| Teal | `#ccfbf1` | `#0f766e` | Bandicoot components |
| Blue | `#dbeafe` | `#2563eb` | Program systems and inputs |
| Slate | `#f1f5f9` | `#64748b` | Storage |
| Violet | `#ede9fe` | `#7c3aed` | People |
| Amber | `#fef3c7` | `#b45309` | Outreach, results, and evaluation |
| Rose | `#ffe4e6` | `#be123c` | Problems and constraints |

- A dashed border means planned (not built).
- Font: `Helvetica,Arial,sans-serif`, 10 pt for nodes, 9 pt for details and edge labels.
- Node labels: a bold title, then one or two short detail lines in gray (`#475569`).
- Each diagram has a title and a one-line subtitle at the top left.
- Label example values as examples. Do not show impact numbers without a source.
- The background is white, so the diagrams stay readable in dark mode.
