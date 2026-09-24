# Success Memory Item 1
## Title
Recognize Declarative Trivia Format
## Description
Identify when a prompt is structured as a factual statement or clue rather than a direct question, indicating an implicit request to supply the missing subject.
## Content
Treat statement-style prompts as fill-in-the-blank or Jeopardy-style queries. Extract the core descriptors (specific works, affiliations, timelines, or actions) to determine which entity is being described, then frame your search and reasoning around identifying that missing subject.

# Success Memory Item 2
## Title
Anchor Retrieval on High-Signal Keywords
## Description
Isolate distinctive, low-frequency terms from the prompt and use them to cross-reference retrieved documents for precise entity matching.
## Content
Prioritize unique identifiers such as song titles, record labels, dates, or locations over generic terms. Scan the context for documents that explicitly link these anchors to a single person or subject, filtering out tangential mentions to confirm the correct target.

# Success Memory Item 3
## Title
Strict Tagged Entity Output
## Description
Deliver the resolved entity concisely within the mandated response tags, avoiding explanatory text or formatting artifacts.
## Content
Once the target is confirmed via context matching, output only the exact name or identifier inside the required `<answer>...</answer>` tags. Omit introductory phrases, reasoning steps, or punctuation outside the tags to ensure compatibility with automated evaluation metrics.
