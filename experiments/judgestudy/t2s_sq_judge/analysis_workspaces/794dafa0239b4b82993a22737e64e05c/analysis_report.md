# Failure Cause Item 1
## Title
Over-specification of Answer Span
## Description
The agent identified the correct shared attribute (being from Massachusetts) but added unnecessary descriptive text ("U.S. Senators from") that exceeded the expected answer granularity.
## Content
The question "Edward Kennedy,John Kerry" implicitly asks for the common entity or location connecting them. The context repeatedly refers to them as "Massachusetts Senator" or "D-Mass." The gold answer is simply "Massachusetts." The agent's reasoning correctly noted phrases like "fellow Massachusetts Senator John Kerry" but failed to extract the minimal span "Massachusetts," instead outputting a longer phrase "U.S. Senators from Massachusetts." This is a span-boundary problem where the agent included role descriptors not present in the gold answer.

# Failure Memory Item 1
## Title
Prefer Minimal Entity Spans for Relation/Connection Questions
## Description
When questions consist of two entities and ask for their connection, the answer is often a single shared entity (location, party, organization) rather than a descriptive phrase.
## Content
In SearchQA items with entity-pair questions, the expected answer is frequently a concise entity name (e.g., "Massachusetts" instead of "U.S. Senators from Massachusetts"). Agents should prioritize extracting the smallest noun phrase that captures the shared attribute, avoiding adding roles or titles unless explicitly required by the context phrasing.

# Failure Memory Item 2
## Title
Adjudicate Between Descriptive Phrases and Core Entities
## Description
When multiple passages describe a relationship using different levels of detail, choose the core entity over descriptive elaborations if the question implies a simple connection.
## Content
Agents should recognize that questions like "Entity A, Entity B" typically seek a single shared attribute. If the context supports both "Massachusetts" and "U.S. Senators from Massachusetts," the shorter form is usually preferred as it represents the fundamental shared entity. The agent should strip modifiers when they are not part of the core answer span.

ACTION: TASK_COMPLETE
