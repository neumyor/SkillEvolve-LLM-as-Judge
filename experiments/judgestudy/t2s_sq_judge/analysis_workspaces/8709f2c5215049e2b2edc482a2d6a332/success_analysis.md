# Success Memory Item 1
## Title
Infer Implicit Query from Declarative Fragments
## Description
Recognize that knowledge prompts may be phrased as incomplete statements or trivia clues rather than direct questions, requiring the model to deduce the missing target entity (typically the creator, originator, or primary subject).
## Content
When a prompt follows a structure like "[Identifier] is the [descriptor] of [Work]", treat the omitted noun as the target answer. Map the given identifiers to the expected entity type using domain conventions, then resolve the query accordingly.

# Success Memory Item 2
## Title
Resolve Entities via Explicit Contextual Mappings
## Description
Utilize direct textual links in the retrieved context that pair alternative titles, dates, or descriptors with a specific creator or source.
## Content
Scan passages for explicit equivalence markers such as "(original title: X)", "Alternative Title: Y", or "by [Author]" to establish unambiguous connections between the prompt's keywords and the target entity. Trust these direct mappings over inferred associations.

# Success Memory Item 3
## Title
Extract Precisely and Format Minimally
## Description
Prioritize exact entity extraction and strict adherence to output constraints, avoiding explanatory text or prompt repetition in the final response.
## Content
Once the target entity is confirmed through context matching, isolate only the precise name or phrase. Wrap it directly in the required tags without additional commentary, step-by-step narration, or restatement of the original prompt.
