# Success Memory Item 1
## Title
Direct Phrase-to-Entity Mapping
## Description
Extract answers by locating the exact descriptive phrase from the prompt within the context and identifying the associated subject in the same snippet or document header.
## Content
Scan retrieved documents for verbatim or highly similar phrasing from the question. Once located, extract the primary entity or title mentioned in immediate proximity or as the source heading. This approach efficiently resolves trivia queries where the context provides explicit factual pairings.

# Success Memory Item 2
## Title
Multi-Snippet Consensus Confirmation
## Description
Strengthen answer confidence by ensuring multiple independent context excerpts consistently link the prompt's unique descriptor to the same target entity.
## Content
After identifying an initial candidate, quickly review other provided documents for the same keyword pairing. Consistent co-occurrence across separate sources eliminates ambiguity, filters out irrelevant matches, and confirms the correct entity before finalizing the response.

# Success Memory Item 3
## Title
Constraint-Compliant Output Generation
## Description
Immediately wrap the confirmed answer in the specified XML tags without additional explanation, reasoning steps, or conversational filler.
## Content
Upon validation, generate only the required tag structure containing the exact entity name. Omit all intermediate thoughts, greetings, or supplementary text to ensure strict compliance with automated parsing and evaluation metrics.
