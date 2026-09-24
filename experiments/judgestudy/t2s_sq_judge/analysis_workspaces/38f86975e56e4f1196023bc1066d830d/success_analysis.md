# Success Memory Item 1
## Title
Leverage Exact Phrase Matches for Trivia Queries
## Description
Recognize when a prompt uses quiz bowl, flashcard, or trivia phrasing, which frequently appears verbatim in search results alongside its answer.
## Content
Scan retrieved snippets for exact or near-exact repetitions of the question text. When a match is found, extract the corresponding answer directly from the same sentence or clause without requiring external knowledge or cross-document synthesis.

# Success Memory Item 2
## Title
Direct Extraction from Declarative Context Snippets
## Description
Prioritize and trust high-confidence declarative statements in retrieved documents that explicitly link a subject to a target answer.
## Content
When a snippet contains a clear subject-answer pairing (e.g., "[SUBJECT] INVENTED [ANSWER]"), treat it as authoritative. Skip multi-step deduction or hypothesis testing, and isolate the precise term requested by the prompt.

# Success Memory Item 3
## Title
Minimize Inference for Direct Context Matches
## Description
Avoid unnecessary reasoning chains when the retrieved context already provides a complete, unambiguous answer.
## Content
Upon locating a direct match, briefly acknowledge the alignment, confirm the output complies with structural requirements (e.g., tag placement, conciseness), and generate the final response immediately. This preserves token efficiency and reduces the risk of hallucination or overcomplication.
