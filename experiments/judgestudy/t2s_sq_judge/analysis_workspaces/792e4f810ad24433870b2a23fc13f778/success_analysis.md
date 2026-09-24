# Success Memory Item 1
## Title
Targeted Keyword Triangulation
## Description
Rapidly isolate the correct context segment by cross-referencing unique temporal markers, proper nouns, and relational phrases from the prompt against retrieved documents.
## Content
Scan all available snippets for the intersection of key entities (e.g., historical names, dates, locations) and action verbs. Prioritize passages that explicitly link these elements in a single declarative statement, bypassing tangential background details or overlapping historical narratives.

# Success Memory Item 2
## Title
Literal Entity Isolation
## Description
Extract the precise noun phrase directly answering the query when the context provides an explicit, unambiguous factual statement.
## Content
Avoid paraphrasing or synthesizing multiple sources when a single sentence directly satisfies the question. Identify the subject or object immediately following relational terms (e.g., "became part of," "formed," "renamed") and isolate it as the core response without adding contextual qualifiers.

# Success Memory Item 3
## Title
Strict Output Adherence
## Description
Enforce exact formatting requirements by wrapping only the extracted answer in the designated tags, excluding all reasoning, commentary, or conversational filler.
## Content
After identifying the target string, immediately apply the required container tags. Verify that the final output contains solely the formatted answer to meet structural constraints and prevent downstream parsing or evaluation failures.
