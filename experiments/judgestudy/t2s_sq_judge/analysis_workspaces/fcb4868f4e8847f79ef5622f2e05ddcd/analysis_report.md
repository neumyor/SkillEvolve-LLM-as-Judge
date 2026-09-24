# Failure Cause Item 1
## Title
Span-format mismatch: agent produced descriptive summary instead of expected entity
## Description
The agent correctly identified Hamburg as Germany's second-largest city and a major European port from the retrieved context, but produced a multi-clause descriptive answer when the benchmark expected a single entity ("Germany"). The agent treated the query "Hamburg" as an open-ended request for a description rather than a factual lookup expecting a specific attribute value.
## Content
The agent's reasoning shows it synthesized information from multiple passages (Wikipedia, Avison Young) into a coherent description. However, in SearchQA, single-entity queries like "Hamburg" typically expect a specific attribute such as the country. The agent did not recognize this convention and instead outputted a natural-language summary. This is a span-selection error where the agent chose an overly broad descriptive span rather than identifying the precise entity the task required.

# Failure Memory Item 1
## Title
Recognize SearchQA expects entity-type answers for single-entity queries
## Description
When the question is a single entity name (e.g., "Hamburg", "Paris"), the expected answer is often a specific attribute like the country, not a descriptive summary. Agents should consider whether the task expects a concise entity label rather than a natural-language description.
## Content
SearchQA questions frequently use single-entity queries where the gold answer is a specific attribute (country, type, date, etc.). Agents should default to extracting the most direct, concise answer supported by the context rather than synthesizing multi-fact descriptions. If the context states "X is the Y in Z", consider whether Z (or another single entity) is the expected answer.

# Failure Memory Item 2
## Title
Prefer exact span extraction over multi-passage synthesis
## Description
When multiple passages support different aspects of an answer, prefer extracting a single exact span from the most authoritative source rather than combining information across passages into a new phrase.
## Content
Synthesizing information from multiple passages can produce accurate but non-matching answers. The benchmark scorer uses exact string matching or fuzzy F1, so synthesized phrases rarely match gold answers even when factually correct. Always extract the shortest, most direct span that answers the question, prioritizing the first/most authoritative passage.

ACTION: TASK_COMPLETE
