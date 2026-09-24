# Question Answering Skill

## Core Retrieval & Reasoning Principles
- **Clue & Entity Recognition**: Treat questions (especially trivia, Jeopardy-style, or incomplete prompts) as direct requests for a specific person, place, title, or concept. Parse the prompt to filter out introductory cues or "fluff" and isolate the core factual query.
- **Implicit Reference Resolution**: Treat demonstratives and anaphors ("this man", "this plant", "this film", "it") as primary query anchors. Crucially, treat the accompanying descriptive clauses as *active filtering constraints*, not noise. Use them to narrow down candidates and discard entities that fail the specific attributes mentioned.

- **Declarative Clue Parsing & Implicit Query Resolution**: Treat declarative statements, descriptive fragments, and Jeopardy-style prompts as direct requests for the *implied* answer, not the stated entity. If the prompt names an entity (e.g., a film, book, or series), determine what is actually being queried about it (e.g., its source material, subject matter, or creator) and extract that target. Never mirror the prompt's explicit noun phrase unless it directly completes the semantic gap.
- **Uniform Clue Processing**: Treat all prompt formats—complete questions, fragmented phrases, declarative statements, headlines, or incomplete prompts—as direct fill-in-the-blank requests. Mentally convert declarative statements or scene descriptions into explicit 'Who/What/Where is X?' queries to isolate the target slot. Strip any parenthetical introductions, speaker credits, category headers, or trailing metadata before parsing. Focus solely on the semantic gap.

- **Meta-Text & Conversational Filler Stripping**: When clues contain director cues, stage directions, conversational asides, or self-referential commentary (e.g., '(Schumacher reads his clue.)', 'hey, it was basically...'), strip these non-factual elements entirely. Focus exclusively on the underlying factual constraints and the semantic gap they define.
- **Direct Extraction Priority**: For declarative trivia prompts, treat the task as a direct lookup rather than a complex reasoning problem. Identify the missing variable and extract the exact verbatim entity from document titles or passage headers. Avoid over-deriving or rephrasing; the correct answer is typically a direct string match present in the context.

- **Declarative Fact Decomposition**: Parse declarative statements and historical facts by isolating the *missing variable* (subject, object, or location) that completes the logical proposition. Map each independent attribute (date, role, ownership, action) to a filtering constraint before searching.

- **Title-Passage Triangulation**: Prioritize document titles (`[TLE]`) as high-signal candidate generators for trivia queries. Use titles to rapidly narrow the search space, then verify constraints against the passage body (`[PAR]`) before finalizing the answer.
- **Direct Extraction & Context Scanning**: Systematically scan `[DOC]`, `[TLE]`, and `[PAR]` blocks for exact keyword matches. When a clue contains multiple independent attributes, actively cross-reference across *multiple* document snippets to intersect constraints. Discard candidates that satisfy only a subset of conditions or belong to a different category.
- **Constraint-Driven Verification & Entity Disambiguation**: Prioritize exact matches for numerical, temporal, or proper-noun constraints. When clues use relative labels like "current," "modern," or "former," cross-reference them with specific historical anchors (dates, events, locations) in the context. Discard candidates that match the label but fail unique factual identifiers, and avoid relying on external knowledge or ambiguous status tags.

## Trivia & Clue Extraction Rules
- **Slot-Filling Strategy**: Treat Jeopardy-style and incomplete prompts as direct fill-in-the-blank requests. Identify the grammatical slot (subject, object, location) being queried and extract the exact term that fills it.

- **List-to-Container Inference**: When a prompt presents a comma-separated list or enumeration of related entities (e.g., characters, locations, works), treat it as a request for the overarching container, series, or category. Infer the parent entity rather than returning the list or individual items.
- **Pun & Riddle Decoding**: Treat playful language, puns, metaphors, or wordplay in clues as semantic descriptors. Map them to their literal factual referents using context verification before extraction. Strip all figurative phrasing from the final answer.

- **Acronym & Abbreviation Expansion**: When clues use acronyms, initialisms, or shortened forms (e.g., PIP, uke, NASA), expand them to their full canonical terms if the context supports it. Prioritize the unabbreviated form unless the gold answer explicitly requires the short version.
- **Playful & Cultural Aside Filtering**: Treat pop-culture references, jokes, historical anecdotes, or non-factual asides in clues as secondary constraints or distractors. Prioritize hard factual anchors (dates, locations, proper nouns, explicit categories) to isolate the target entity, and strip away any humorous or conversational framing from the final answer.
- **Proverb, Quote & Idiom Resolution**: Treat famous quotes, proverbs, idioms, and song lyrics as direct queries for their underlying subject or concept. Strip attribution cues (e.g., 'According to...', 'It's the cry of') and resolve the semantic gap to the specific entity or idea being described.

- **Demonstrative-Category Anchoring**: When clues use phrases like 'this film series', 'one of these bombs', or 'the Denver type of this', treat the demonstrative + category noun as a direct pointer to the target class. Isolate the specific instance within that class that satisfies the unique constraints provided.
- **Clue Syntax Mapping**: Use structural cues like "this film", "it's the cry of", or "named for" to determine the expected answer type. Isolate the specific query target when multiple entities or conditions are present; do not return any entity merely mentioned in the prompt.

- **Category, Syntactic & Morphological Alignment**: Verify that the candidate entity matches the exact grammatical role, categorical type, and number agreement implied by the clue (e.g., person vs. place, singular vs. plural, city vs. state). Discard candidates that satisfy factual constraints but fail the syntactic, categorical, or morphological filter.

- **Multi-Constraint Synthesis**: When a clue provides multiple independent attributes (e.g., date, role, location, party, quantity), intersect these constraints to isolate the single matching entity. Discard candidates that satisfy only a subset of conditions.
- **Canonical Phrasing & Granularity Alignment**: Prioritize exact canonical string matching over heuristic expansion or contraction. Trivia and Jeopardy answers often require specific articles, honorifics, titles, or full names (e.g., "Sir Isaac Newton", "the Amazon", "a eucalyptus tree") that must be preserved exactly. Do not strip titles, articles, or generic descriptors (like "River" or "Speech") unless explicitly instructed by the clue. Conversely, do not append explanatory modifiers or default to full names if the canonical answer is a surname or short phrase. Match the exact capitalization, plurality, and phrasing of the expected answer.

- **Strict Canonical Truncation**: When extracting titles, organizations, or concepts, prefer the recognized short or canonical form over the full descriptive title. Do not append categorical nouns (e.g., "Party", "Show", "Structure", "Book") or prepositional phrases unless they are strictly part of the official short name (e.g., output "Bull Moose" not "Bull Moose Party", "Studio 60" not "Studio 60 on the Sunset Strip", "Pyre" not "funeral pyre").

- **Preservation of Standard Prefixes**: Do not strip standard geographical, administrative, or institutional prefixes (e.g., "Lake," "Mount," "St.," "Republic," "People's") when they constitute the recognized canonical name. Prioritize exact lexical matching over heuristic shortening.
- **Formal vs. Alias Resolution**: When both a formal/full name and a common alias or foreign variant appear in the context, prioritize the formal English name for historical/trivia queries (e.g., "Patricia Hearst" over "Patty Hearst", "Pitti Palace" over "Palazzo Pitti") unless the clue explicitly signals the alias or foreign term.

- **Predicate-Entity Alignment**: Before extracting, verify that the candidate entity actually performs, possesses, or is located at the specific attribute/action described in the clue. Do not select an entity simply because it shares keywords with the prompt; confirm the semantic relationship holds in the context.
- **Noise Filtering**: In search-result-style or repetitive contexts, rapidly scan titles and snippets for exact keyword matches, then verify in the passage body before extracting. Ignore duplicated passages.
- **No Syntactic Mirroring & Category Exclusion**: Never repeat the prompt's phrasing, complete sentences grammatically, or append categorical nouns/classifiers explicitly stated in the clue (e.g., output "bear" not "bear market", "Minsk" not "Capital cities"). Treat the prompt's category label as a structural pointer, not part of the answer. Output only the isolated entity requested.
- **Gold Alignment & Morphological Precision**: Match the granularity, capitalization, and morphological form (singular/plural) of the expected answer exactly. Do not force syntactic agreement with the clue if it conflicts with the canonical form; prioritize the exact lexical item (e.g., singular vs. plural, verb vs. adjective) over grammatical consistency with the prompt.

- **Article Omission Tolerance**: For F1-based evaluation, safely omit leading indefinite or definite articles (e.g., "a", "the") unless the clue's syntax strictly requires them for grammatical completion. Prioritize the core lexical item and canonical spelling over strict article preservation.
- When multiple entities appear in the context, select the one that directly completes the clue or matches the expected brevity.
- Strip modifiers and use only surnames or key terms if the gold answer is minimal (e.g., output "C" not "Vitamin C", "Genet" not "Jean Genet").
- Do not guess based on metaphorical phrasing without verifying factual alignment.
- Avoid converting declarative clues into Yes/No answers.

## Answer Formatting Rules
- **Strict Tag Usage**: Always wrap the final answer in `<answer>...</answer>` tags.
- **Conciseness & Minimal Entities**: Prioritize exact, minimal entity extraction. The content inside tags must be the exact entity or a very short phrase. Preserve standard capitalization, omit leading articles unless integral, and avoid full sentences, explanations, or conversational filler. Never repeat the question's phrasing or append contextual modifiers to the answer. Ensure zero-leakage by stripping any leading labels, reasoning fragments, trailing punctuation, or prompt artifacts before closing the tag.

- **Zero-Leakage Enforcement**: Never include reasoning steps, conversational framing, or transitional phrases inside `<answer>` tags. The tag content must contain ONLY the isolated entity or phrase. Place all derivation logic strictly outside the tags.
- **Minimal Reasoning**: Skip verbose derivations for straightforward retrieval tasks. If step-by-step reasoning is performed, place it outside the answer tags and keep it brief.

- **Semantic Category Constraint Verification**: Cross-check the clue's explicit categorical keywords (e.g., "acid", "tree", "artist", "river") against candidate entities. If a clue specifies a type (e.g., "caustic acid"), discard candidates that belong to a different category (e.g., "caustic soda"/base) even if they share other attributes. Ensure the selected entity strictly satisfies the semantic type requested by the prompt.

- **Container-Part Disambiguation**: When a clue references a sub-component, building, or feature located *within* a larger site or entity (e.g., 'building at this site'), always resolve the query to the *container* or *primary subject* requested by the prompt's anchor. Do not answer with the sub-component itself.

- **Attribute vs. Container Resolution**: When a clue references a collective, organization, or container and queries its constituent parts or defining attributes (e.g., "alliance of these Chinese businesses"), isolate the specific attribute, type, or component requested. Do not default to the overarching entity name unless it directly fills the semantic gap.

- **Canonical Name & Variant Handling**: When extracting names or terms with multiple textual variants, aggressively strip middle initials, middle names, and redundant category nouns (e.g., "Mint", "Cards", "Kings"). Prioritize the concise, widely recognized canonical form that aligns with standard trivia usage. Preserve necessary definite articles only if integral to the canonical name (e.g., "the Adirondacks"). For synonymous terms, select the variant that best matches the clue's specific descriptors rather than mirroring contextual strings.

- **Pronoun & Possessive Resolution**: Treat possessive pronouns ("his", "her", "their") and standalone subject pronouns ("it", "he") in declarative clues as primary query anchors. Map them to the missing entity and use the accompanying descriptive clauses as active filtering constraints, just as with demonstratives.
