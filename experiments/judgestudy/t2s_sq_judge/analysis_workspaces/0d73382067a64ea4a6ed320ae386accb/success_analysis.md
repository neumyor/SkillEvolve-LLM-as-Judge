# Success Memory Item 1
## Title
Interpret Fragmented Date/Location Prompts as Trivia Queries
## Description
Recognize when a user input consists solely of a date, place, or phrase lacking explicit interrogative structure, and reframe it as a request for the most salient historical figure or event associated with those parameters.
## Content
When presented with isolated temporal or spatial markers, scan the context for the dominant subject repeatedly tied to those markers. Treat the prompt as a factual lookup and extract the core entity or event name as the direct answer, bypassing unnecessary syntactic parsing.

# Success Memory Item 2
## Title
Leverage Cross-Source Consensus for Definitive Answers
## Description
Prioritize facts that appear consistently across multiple independent context passages, using repetition as a signal of relevance and accuracy over isolated or tangential mentions.
## Content
In retrieval-augmented settings, multiple documents often echo the same core fact. Identify overlapping statements regarding the target parameters, filter out peripheral details (e.g., family names, career paths, or unrelated historical notes), and anchor the final response strictly to the universally confirmed subject.

# Success Memory Item 3
## Title
Output Minimal Named Entities for Direct Slot Alignment
## Description
Format responses as concise, exact entity names rather than full sentences or explanatory phrases to ensure direct alignment with the expected factual slot.
## Content
For parameter-based or trivia prompts, strip away conversational framing and deliver only the primary noun phrase. This maintains strict conciseness, eliminates ambiguity, and ensures the response precisely fills the implicit blank left by the prompt structure.
