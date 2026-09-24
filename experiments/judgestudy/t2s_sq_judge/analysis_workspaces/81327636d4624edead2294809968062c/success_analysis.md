# Success Memory Item 1
## Title
Parody-to-Canonical Title Resolution
## Description
Map altered or punned titles referenced in prompts back to their original canonical names using contextual evidence.
## Content
When a question describes a title modification (e.g., word substitution, phonetic play), locate the altered version in the retrieved context. Extract the original canonical title it references, ensuring the answer aligns with the specified category (e.g., literary work, film, play). Reverse-engineer the clue to confirm the mapping is accurate before finalizing.

# Success Memory Item 2
## Title
Exact-Clue Context Anchoring
## Description
Isolate the definitive answer source by matching specific prompt keywords directly to context snippets.
## Content
Prioritize context passages that explicitly contain both the unique clue phrasing and the target entity. Use direct textual overlap to bypass ambiguous or tangential results. When multiple documents appear, select the snippet that explicitly states the relationship between the clue and the answer rather than inferring from partial matches.

# Success Memory Item 3
## Title
Constraint-Aligned Output Generation
## Description
Confirm the extracted answer against all prompt constraints before wrapping it in the required format.
## Content
Before outputting, confirm that the selected string precisely matches the requested entity type, satisfies temporal or categorical qualifiers, and contains no extraneous information. Strip surrounding context, synonyms, or explanatory phrases. Enclose only the clean, confirmed answer within the designated tags to meet strict formatting requirements.
