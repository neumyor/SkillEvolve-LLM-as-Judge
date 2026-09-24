# Success Memory Item 1
## Title
Geographic Scope Alignment
## Description
Match the administrative level specified in the prompt against candidate entities to prevent scope mismatches.
## Content
When questions reference a specific geographic tier (e.g., country, state, city), explicitly filter candidates to ensure the selected entity operates at that exact level. Discard nested or broader alternatives that may appear prominently in the context but do not satisfy the stated scope.

# Success Memory Item 2
## Title
Phrasal Mirroring Extraction
## Description
Locate answers by identifying structural and lexical parallels between the question stem and retrieved context.
## Content
For factoid or cloze-style prompts, scan context snippets for sentences that closely replicate the question's syntax. The term filling the conceptual gap in the matching context phrase typically serves as the direct answer, minimizing inference overhead.

# Success Memory Item 3
## Title
Constraint-First Output Generation
## Description
Isolate the final answer from internal reasoning and enforce strict formatting rules before submission.
## Content
Separate analytical steps from the deliverable. Apply required wrappers (e.g., specific tags) and ensure the final output contains only the requested information, stripping all intermediate logic, justifications, or conversational filler.
