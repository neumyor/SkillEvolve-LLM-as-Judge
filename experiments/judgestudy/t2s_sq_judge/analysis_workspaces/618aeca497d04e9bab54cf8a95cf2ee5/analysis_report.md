# Failure Cause Item 1
## Title
Over-specification of Entity Name Span
## Description
The agent correctly identified the target entity but selected a longer, less canonical span ("McCormick & Company") instead of the shorter, more frequent form ("McCormick") present in the context and expected by the benchmark.
## Content
The agent's reasoning correctly linked Schilling ownership and dehydrated garlic/onion production to McCormick. However, it committed to the full corporate name "McCormick & Company" rather than the simpler "McCormick". While both refer to the same entity, the gold answer and the majority of context snippets use "McCormick" alone. This is a span-selection error where the agent included extraneous nominal modifiers (& Company) that were not part of the minimal correct answer span.

# Failure Memory Item 1
## Title
Prefer Minimal Canonical Entity Spans
## Description
When multiple valid spans refer to the same entity, prefer the shortest, most frequently occurring canonical name in the context over longer descriptive variants.
## Content
In SearchQA-style tasks, exact match scoring requires precise span alignment. Agents should scan the context for the most concise form of the entity name (e.g., "McCormick" vs "McCormick & Company", "NYC" vs "New York City") and prioritize that minimal span unless the question specifically demands the full legal name.

# Failure Memory Item 2
## Title
Verify Answer Granularity Against Context Frequency
## Description
Cross-check the chosen answer span against its frequency in the retrieved documents; the most common short form is often the intended gold answer.
## Content
If the context repeatedly uses a short entity name (e.g., "McCormick") while also mentioning a longer variant (e.g., "McCormick & Company"), the short form is statistically more likely to be the gold answer. Agents should default to the high-frequency minimal span to maximize EM scores.

ACTION: TASK_COMPLETE
