# SearchQA Question Answering

## Read the Evidence

- **Prioritize Verbatim Alignment:** Scan retrieved documents for exact or near-exact phrase matches with the prompt. Trivia and factoid queries often reuse published phrasing; treat verbatim overlaps as high-confidence signals for locating the answer.
- **Leverage Cross-Source Consensus:** Validate candidate answers by checking for consistent mentions across multiple independent context snippets. If several retrieved passages independently reference the same entity using consistent terminology, treat this convergence as sufficient grounds for selection.
- **Trust Structured Data Formats:** Identify and exploit standardized separators (e.g., pipes, colons) or Q&A structures in retrieved trivia or dataset contexts. When processing quiz-style questions, scan for explicit delimiter characters that separate the prompt from the target response and extract the exact string immediately following these markers.

## Answer Format

- **Step-by-Step Reasoning:** Think step by step, analyzing the prompt constraints and evidence before generating the final output.
- **Strict Tag Encapsulation:** Place the final answer inside `<answer>...</answer>` tags. Do not repeat the question, add explanations, or include conversational filler inside the tags.
- **Conciseness:** Keep the answer concise—typically a few words or a short phrase. Avoid full sentences unless the question explicitly requires a description.

## Entity Extraction Rules

- **Prefer Minimal Entity Spans:** When multiple valid text spans identify the same entity, select the shortest one that is unambiguous in context. Avoid adding descriptive modifiers, dates, or titles unless they are integral parts of the proper noun itself.
- **Exclude Generic Categories:** When the context describes an entity as "[Entity] [Category]" (e.g., "U2 Tribute Band"), the answer should typically be just "[Entity]", excluding the common noun classifier unless the question explicitly asks for the type.
- **Handle Metadata Suffixes:** Ignore trailing numbers, point values, or database categorization words (e.g., "Network," "TV Series," "Show") that are part of the listing label rather than the entity's actual name.
- **Preserve Definite Articles:** Include leading definite articles ("the", "a") if they appear as part of the natural noun phrase in the source text, especially for institutional names where the article is part of the canonical form.
- **Match Grammatical Number:** Ensure the answer span matches the grammatical number (singular vs. plural) implied by the question. If the question asks for "one of these X," the answer should be singular.
- **Resolve Nicknames and Aliases:** Map informal terms, slogans, or cultural references to their formal identifiers by locating explicit pairings within the retrieved text. If the question asks for a nickname, extract the specific term used as the substitute name, not the combination of the nickname and surname.

## Context Analysis Strategies

- **Filter Distractors:** Systematically rule out entities that share superficial keywords but fail to meet core temporal, geographic, or positional requirements. Discard partial matches where only some operations or attributes align.
- **Distinguish Container vs. Contained Entities:** In questions asking for a "site" or "location" containing a specific feature, the answer is the site/location, not the feature itself. The feature serves as a descriptor/clue.
- **Map Entity Pairs to Shared Attributes:** For terse questions formatted as "Entity A & Entity B," prioritize identifying a shared attribute (nationality, profession, location) over describing the interpersonal relationship between entities.
- **Interpret Declarative Prompts:** Treat prompts structured as factual statements, quotes, or incomplete sentences as implicit requests to identify the missing subject or attribute. Infer the underlying information-seeking goal to guide extraction.

## Prompt Parsing

- **Recognize Trivia Clues:** Identify when prompts use quiz bowl, flashcard, or Jeopardy-style phrasing. These typically expect a single definitive entity or short phrase rather than open-ended analysis.
- **Parse Fill-in-the-Blank Structures:** Carefully parse which entity the sentence structure is requesting. Phrases like "The X of this Y is Z" often ask for Y (the container/territory) rather than X (the specific institution).
- **Decode Quoted Terms:** Treat words enclosed in quotation marks within trivia prompts as indicators of wordplay, literal references, or specific named entities rather than their standard dictionary definitions.
