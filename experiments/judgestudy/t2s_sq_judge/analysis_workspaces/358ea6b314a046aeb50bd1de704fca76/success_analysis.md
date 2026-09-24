# Success Memory Item 1
## Title
Resolve Implicit Query Intent
## Description
When prompted with a declarative statement rather than a direct question, infer the underlying information-seeking goal to guide extraction.
## Content
Treat prompts structured as facts or partial sentences (e.g., "His middle name was X") as implicit identification requests. Map the given attribute to the expected subject slot and search the context for entities that satisfy the relationship, ensuring the final response directly names the missing subject.

# Success Memory Item 2
## Title
Prioritize Explicit Contextual Assertions
## Description
Extract answers by locating direct, unambiguous statements in the retrieved text that explicitly link the target attribute to an entity.
## Content
Scan context snippets for phrases that contain both the key identifier and the target concept (e.g., "[Entity]'s middle name was [Attribute]"). Rely on these direct textual alignments as the primary evidence source, bypassing complex reasoning or external knowledge when the context already contains a clear match.

# Success Memory Item 3
## Title
Enforce Strict Output Delimiters
## Description: Guarantee format compliance by wrapping the final answer in the exact tags specified by the prompt.
## Content: Before generating the response, verify that the extracted answer string is enclosed within the required markup (e.g., `<answer>...</answer>`). Apply this structural constraint consistently to prevent parsing failures that can override otherwise correct content extraction.
