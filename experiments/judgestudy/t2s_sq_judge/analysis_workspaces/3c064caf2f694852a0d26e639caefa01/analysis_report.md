# Failure Cause Item 1
## Title
Span-Selection Mismatch: Agent Chose Longer Canonical Phrase Instead of Short Form

## Description
The agent correctly identified the target entity (hydroelectric power/hydropower) and selected "Hydroelectric power" as the answer span. However, the expected answer is "hydroelectric" — a shorter, more concise form. The agent's reasoning was sound: it found passages stating "Hydroelectric power is the largest source of renewable electricity" and confirmed pumped-storage is a type of hydroelectric plant. The failure is purely a span-boundary issue: the agent committed to a two-word phrase when the question's phrasing ("Pumped-storage is one type of plant for **this**") implies a single-word or short entity name.

## Content
The agent trusted the correct passages ([DOC] Hydroelectric power in the United States, [DOC] Hydropower Technology Development | Department of Energy) and correctly linked pumped-storage to hydroelectric power. It chose "Hydroelectric power" as the answer span based on explicit context support. The diagnosis is that the agent did not consider that SearchQA answers often use shortened forms (e.g., "hydroelectric" vs. "Hydroelectric power"). This is a near-miss: the answer overlaps the right entity but differs in span length. The agent committed to an answer at all, and the choice was reasonable given the context — it just didn't match the expected brevity.

# Failure Memory Item 1
## Title
Prefer Concise Answer Spans When Question Phrasing Implies Single Entity

## Description
When a question uses phrasing like "for this" or "what is X," the expected answer is often a single word or short phrase rather than a multi-word descriptive term. Agents should prioritize the most concise span that captures the entity, especially when synonyms or longer forms exist in the context.

## Content
In this case, "hydroelectric" is the expected answer while "Hydroelectric power" was produced. Both are semantically correct and supported by context. The lesson: when selecting an answer span, check whether the question's grammar suggests a short form (noun/adjective used as noun) versus a full descriptive phrase. If multiple valid spans exist, prefer the shortest one that stands alone as a complete answer.

# Failure Memory Item 2
## Title
Near-Miss Failures Are Span-Boundary Problems, Not Retrieval Errors

## Description
When an agent produces an answer that is semantically correct but differs in wording or length from the expected answer, diagnose it as a span-selection issue rather than a wrong-entity or wrong-passage error. The agent successfully retrieved relevant context and identified the correct concept; the failure lies only in how much text was included in the final answer span.

## Content
This applies broadly to SearchQA items where agents produce "Hydroelectric power" instead of "hydroelectric," "renewable energy" instead of "solar," etc. The key diagnostic question is: does the answer refer to the correct entity? If yes, the problem is span boundaries. If no, investigate passage selection and entity disambiguation. Always report the specific decision (span choice) that led to the mismatch, not just the fact that the answer differs from gold.

ACTION: TASK_COMPLETE
