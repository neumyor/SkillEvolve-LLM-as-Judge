# Success Memory Item 1
## Title
Rapid Entity Mapping via Verbatim Context Anchors
## Description
Use exact question phrasing or distinctive keywords in retrieved text to instantly locate the target entity, prioritizing document titles and adjacent metadata.
## Content
When a query contains specific names, dates, or titles that appear verbatim in the context, treat the task as a direct lookup. Scan for the matching phrase and extract the associated proper noun or identifier presented in the document title or immediate surrounding text. This bypasses unnecessary inference and accelerates accurate extraction.

# Success Memory Item 2
## Title
Contextual Lookup for Factual and Trivia Prompts
## Description
Recognize quiz-style or factual recall questions as lookup tasks when the context provides explicit structural cues like titles or repeated prompt fragments.
## Content
For questions framed as trivia or fill-in-the-blank statements, rely on the context's explicit labeling mechanisms. Document titles often contain the direct answer, while paragraph text may repeat the query verbatim. Align the query's subject with these labeled anchors to derive the answer efficiently without relying on external knowledge assumptions.

# Success Memory Item 3
## Title
Direct Extraction and Schema Enforcement
## Description
Confirm the extracted entity satisfies the query's core constraints and immediately apply the required output structure.
## Content
Once the context points to a specific entity through titles or exact phrase matches, confirm it only against the question's explicit parameters. Skip extended reasoning chains. Immediately wrap the result in the mandated tags to ensure compliance and maintain processing efficiency.
