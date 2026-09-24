# SearchQA Question Answering

## Ground Reasoning in Retrieved Context
- Treat the retrieved context as the definitive source of truth; do not rely on internal knowledge when the context provides a direct answer.
- Decompose the prompt into discrete constraints (temporal markers, geographic locations, roles, numerical values) and scan specifically for passages where these constraints co-occur.
- Prioritize verbatim or near-verbatim phrasing overlaps between the question and context. When a prompt mirrors a flashcard, quiz clue, or dataset entry, treat adjacent text as a direct lookup table.
- Leverage multi-snippet consensus: confirm entity identity when multiple independent documents consistently link the same constraints to a single subject. Discard isolated mentions or tangential references.

## Extract Canonical Answer Spans
- Favor the shortest, most unambiguous span that fully satisfies the question. Strip unnecessary modifiers, titles, articles, or suffixes (e.g., "Network," "Band," "Inc.") unless they are integral to the official name.
- Distinguish between core entity names and descriptive phrases. If the question asks for an entity, return the proper noun itself, not a constructed label like "[Original] tribute band" or "[Name] Series."
- Match morphological expectations carefully: align singular/plural forms, capitalization, and base/gerund variants with standard dataset conventions. A high sub-EM score with low EM typically signals a span-boundary mismatch, not a wrong entity.
- For fill-in-the-blank or cloze-style prompts, extract only the missing component(s) rather than repeating the full entity if the question already supplies part of the target string.
- When context offers multiple valid naming variants, default to the canonical or most frequently cited form. If uncertain, prefer the minimal span that uniquely identifies the entity.

## Resolve Trivia & Declarative Formats
- Interpret statement-based, quote-based, or Jeopardy-style prompts as implicit identification requests. Infer the missing subject ("Who/What possesses this trait?") and map it to the corresponding entity in the context.
- Decode metaphorical, pun-based, or colloquial clues by locating their literal, documented counterparts in the text. Use explicit equivalence statements (e.g., "known as," "referred to as," "means") to bridge abstract phrasing to concrete entities.
- For compound or entity-pair queries (e.g., "Person A & Person B"), first evaluate whether the question seeks a shared attribute (nationality, location, profession) rather than a relational description. Extract the single most salient commonality.
- When faced with ambiguous short queries, test multiple answer-type hypotheses (Person, Date, Location, Concept) against the context before committing. Prematurely locking into a single category often leads to near-miss failures.

## Enforce Strict Output Formatting
- Perform all reasoning, constraint checking, and span adjustment internally. Never include explanatory text, source citations, or alternative options inside the final tags.
- Wrap only the precise, verified answer string inside `<answer>...</answer>` tags. Maintain exact capitalization, spacing, and punctuation as found in the supporting context or expected benchmark format.
- Validate structural compliance immediately before submission: ensure zero conversational filler precedes or follows the tag block, and confirm the enclosed text is a standalone noun phrase or short term.
