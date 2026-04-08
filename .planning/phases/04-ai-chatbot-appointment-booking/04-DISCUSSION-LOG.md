# Phase 4: AI Chatbot + Appointment Booking - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion history.

**Date:** 2026-04-08
**Phase:** 04-ai-chatbot-appointment-booking
**Mode:** discuss
**Areas discussed:** LLM Backend, Knowledge Base format, Booking conversation flow, Admin Inbox UX

---

## Areas Discussed

### LLM Backend
| Question | Options Presented | User Selection |
|----------|------------------|----------------|
| Which LLM backend? | OpenAI gpt-4o-mini / Ollama llama3.2:3b / Start with OpenAI + Ollama later | User initially chose MiniMax API (had API key) |
| Which MiniMax model? | MiniMax-Text-01 / abab6.5s-chat / You decide | User clarified: wants Ollama local consuming MiniMax M2.7 |
| Clarification: What setup? | MiniMax API direct / Ollama local with downloadable model / MiniMax + OpenAI compat | Ollama local with downloadable model |
| Which Ollama model? | llama3.2:3b / mistral:7b / phi-3-mini:3.8b | User pivoted: Ollama not feasible on server — use OpenAI |
| Which OpenAI model? | gpt-4o-mini / gpt-4o | gpt-4o-mini |

**Decision:** OpenAI gpt-4o-mini via n8n native OpenAI node.
**Reason:** Ollama cannot be installed on the current server setup; user confirmed OpenAI as fallback.

---

### Knowledge Base format
| Question | Options Presented | User Selection |
|----------|------------------|----------------|
| Where are FAQs stored? | Static file in n8n / PostgreSQL table | PostgreSQL table manageable via Streamlit |
| Who updates FAQs? | Clinic owner via Streamlit / Technician only | Clinic owner from Streamlit UI |

**Decision:** `knowledge_base` PostgreSQL table with Streamlit admin page (`6_Knowledge_Base.py`).

---

### Booking conversation flow
| Question | Options Presented | User Selection |
|----------|------------------|----------------|
| How does booking conversation work? | Natural free-text (LLM extracts) / Guided menu (numbered options) | Natural conversation — LLM extracts data |
| What info does bot collect? | Fecha/hora + tipo de servicio / Solo fecha/hora | Fecha/hora + tipo de servicio |

**Decision:** Natural conversation, LLM extracts service type + preferred date/time. Patient name auto-filled from DB if phone matches; asked if not found.

---

### Admin Inbox UX
| Question | Options Presented | User Selection |
|----------|------------------|----------------|
| Inbox layout? | Split-pane (list + chat) / Expandable table | Split-pane with st.columns([1, 2]) |
| How to close a conversation? | Button "Cerrar conversación" / Auto-close after inactivity | Manual button in chat view |
| Refresh frequency? | Polling every 10s / Manual refresh button | Polling every 10 seconds |

**Decision:** Split-pane Streamlit page, `[!]` for human_handoff conversations at top, manual close button, 10s auto-refresh.

---

## Corrections Made

No corrections — decisions evolved through clarification (MiniMax → OpenAI pivot was a clarification of technical constraints, not a reversal of a clear decision).

---

## Deferred Ideas

- MiniMax API — user mentioned initially; deferred (OpenAI chosen for feasibility)
- Automatic conversation close on inactivity — raised during inbox discussion; deferred to v2
- WhatsApp button/list menus for booking — natural conversation chosen instead; deferred
