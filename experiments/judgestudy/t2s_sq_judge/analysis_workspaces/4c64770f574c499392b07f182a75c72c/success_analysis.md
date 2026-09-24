# Success Memory Item 1
## Title
Account for Dated Temporal Markers in Trivia Prompts
## Description
Treat temporal qualifiers like "current" or "present" as relative to the question's original publication or broadcast date rather than strictly adhering to present-day facts when resolving ambiguous entities.
## Content
When multiple candidates satisfy the descriptive criteria, evaluate the likely origin era of the prompt. Prioritize the entity that aligns with the historical timeframe implied by the phrasing, especially when context snippets consistently associate the descriptors with a specific historical figure. This prevents over-indexing on modern successors when the query targets a past-era reference.

# Success Memory Item 2
## Title
Cross-Reference Exact Descriptor Clusters
## Description
Isolate unique combinations of proper nouns and attributes from the prompt, then scan retrieved context for documents that explicitly link them to a single named entity.
## Content
Extract key identifiers (e.g., educational institutions, titles, geographic markers). Filter context passages to find those containing the complete cluster of identifiers. Use explicit co-occurrence in the text as the primary selection criterion, disregarding partial matches, tangential references, or entities that only share one attribute with the prompt.

# Success Memory Item 3
## Apply Genre-Convention Heuristics for Disambiguation
## Description
Use structural and stylistic cues common to specific question formats (e.g., quiz bowl, Jeopardy, trivia databases) to determine the expected level of prominence or specificity required for the answer.
## Content
Recognize formulaic phrasing patterns that signal a particular answer type or historical focus. When factual overlap exists between candidates, default to the most frequently cited or culturally prominent figure in public knowledge sources, as these formats typically target widely recognized entities over niche or successor figures. Align the final selection with the genre's standard expectations for answer breadth and recognition.
