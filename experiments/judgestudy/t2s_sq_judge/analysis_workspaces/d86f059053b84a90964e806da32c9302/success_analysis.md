# Success Memory Item 1
## Title
Resolve Ambiguous or Truncated Prompts via Keyword Mapping
## Description
When a question lacks a clear interrogative structure or appears incomplete, infer the intended target by matching unique descriptive phrases to the most salient entity in the context.
## Content
Extract distinctive nouns and events from the prompt (e.g., character name, specific plot event) and search the retrieved context for the primary subject or work associated with them. Default to returning the core entity (e.g., title, author, person) rather than guessing at implicit true/false or multi-part requirements, treating the prompt as a factual identification request.

# Success Memory Item 2
## Title
Anchor Answers to Explicit Contextual Matches
## Description
Use high-confidence contextual signals to verify the relationship between prompt elements and potential answers before finalizing output.
## Content
Scan retrieved documents for direct statements linking the prompt's key terms to a candidate answer. Prioritize authoritative or summary-style snippets that explicitly name the target entity alongside the described event, ensuring the answer directly satisfies the prompt's implied request without overcomplicating or introducing external knowledge.

# Success Memory Item 3
## Title
Enforce Strict Conciseness for Entity-Focused Queries
## Description
Strip narrative explanations and secondary details when the prompt structure implies a direct factual lookup, adhering to minimal viable answer formats.
## Content
Identify when a query functions as a straightforward recall or identification task. Discard tangential context (e.g., character fate nuances, thematic analysis, or chapter specifics) and output only the precise identifier requested. Wrap the final term in the required tags to maintain structural compliance while maximizing retrieval compatibility.
