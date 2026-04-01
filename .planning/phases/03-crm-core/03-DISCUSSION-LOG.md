# Phase 3: CRM Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 03-crm-core
**Areas discussed:** CSV Import UX, Patient List + Search, Tag Management, Template Editor UX

---

## CSV Import UX

| Option | Description | Selected |
|--------|-------------|----------|
| Preview + confirm | Show first N rows normalized, summary counts, then "Importar" button | ✓ |
| Import immediately, show results after | Upload → process → show summary, no preview step | |

**User's choice:** Preview + confirm
**Notes:** Admin sees rows with status badges (Nuevo/Duplicado/Error) before committing.

### Duplicate Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently, count in summary | Don't import, show "3 duplicados ignorados" in summary | ✓ |
| Flag for manual review | Show duplicates in a "Conflictos" section, let admin decide per-row | |

**User's choice:** Skip silently, count in summary

---

## Patient List + Search

### Table Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Dataframe table + filters at top | st.dataframe with search bar + tag multiselect filter above | ✓ |
| Cards grid with modal detail | Patient cards, click to open detail modal | |

**User's choice:** Dataframe table + filters at top

### Tag Assignment

| Option | Description | Selected |
|--------|-------------|----------|
| Checkbox row select + bulk tag action | Select rows → pick tags → "Asignar etiquetas" | ✓ |
| Inline per-row tag multiselect | Each row has its own tag multiselect | |

**User's choice:** Checkbox row select + bulk tag action

### Pagination

| Option | Description | Selected |
|--------|-------------|----------|
| 25 per page | LIMIT/OFFSET queries, manageable chunk | ✓ |
| 50 per page | Fewer page turns for large lists | |
| You decide | Claude picks default | |

**User's choice:** 25 per page

### Import Entry Point

| Option | Description | Selected |
|--------|-------------|----------|
| "Importar pacientes" button in patient list header | Single entry point, stays in context | ✓ |
| Separate sidebar page | Import is its own navigation item | |

**User's choice:** Button in patient list header

---

## Tag Management

### Location

| Option | Description | Selected |
|--------|-------------|----------|
| Inline from patient list | "Nueva etiqueta" form in tag filter section, no separate page | ✓ |
| Dedicated Tags sidebar page | Separate navigation item for tag CRUD | |

**User's choice:** Inline from patient list

### Delete Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Block delete, show count | "Esta etiqueta está asignada a N pacientes. Elimina las asignaciones primero." | ✓ |
| Delete and unassign silently | Cascade delete patient_tags rows without warning | |

**User's choice:** Block delete, show assignment count

---

## Template Editor UX

### Preview Style

| Option | Description | Selected |
|--------|-------------|----------|
| Live side-by-side preview | Editor left, rendered preview right, updates as admin types | ✓ |
| Edit then preview step | Fill form → click "Previsualizar" → see result below | |

**User's choice:** Live side-by-side preview

### Variable System

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed set: {{nombre}}, {{fecha}}, {{clinica}} | Only recognized vars replaced; unrecognized gets warning badge | |
| Open — any {{variable}} is valid | Admin can invent variable names; Phase 5 substitutes them | ✓ |

**User's choice:** Open variable system

### Category Field

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — category dropdown (general / promoción / recordatorio) | Uses existing category TEXT column in schema | ✓ |
| No — skip for now | Defer category to Phase 5 | |

**User's choice:** Yes, include category dropdown

---

## Claude's Discretion

- Color picker implementation
- Preview sample values for variables
- Column widths and table styling
- Error message wording for bad CSV rows
- Phone normalization logic details

## Deferred Ideas

- Patient opt-in/opt-out consent management — v2 (PRIV-01)
- Patient detail/edit page — not in Phase 3 success criteria
- Template versioning — not MVP
- Bulk patient export to CSV — not required for Phase 3
