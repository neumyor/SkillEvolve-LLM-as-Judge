# Question Answering Skill

# Question Answering Skill

## Trivia & Clue Interpretation
- **Fragment Recognition**: Questions often appear as definitions, sentence completions, or trivia clues. Identify the exact entity, term, or concept that completes the clue.
- **No True/False**: Never answer "Yes" or "No" to statement-style clues. Always extract the target subject or entity.
- **Role & Title Matching**: If the clue describes a role (e.g., "this editor"), return the exact role/title used in the context, not a guessed external name.
- **Strip Conversational Framing**: Ignore introductory phrases or conversational wrappers. Focus solely on the core factual query embedded in the clue.

## Extraction & Precision Rules
- **Minimal Span**: Extract the shortest text span that directly answers the question. Avoid pulling full sentences, definitions, or descriptive clauses.
- **Exact Context Match**: Always extract the exact word or phrase used in the `[DOC]`/`[PAR]` blocks. Do not substitute synonyms or add qualifiers (e.g., use 'Football' not 'American Football', 'Soccer' not 'Association Football').
- **Grammatical Exactness**: Match the singular/plural form and specificity of the gold answer. If the context uses "Brown pelican", return "Brown pelican", not "Pelican". If the clue implies a plural, return the plural.
- **Name & Entity Granularity**: Match the name format implied by the clue. Do not substitute a specific example mentioned in the text for a general category (or vice versa) unless explicitly asked.
- **Foreign Titles & Quotes**: Preserve original titles, quotes, or non-English terms exactly as they appear in the context or clue. Do not translate or paraphrase unless explicitly asked.
- **Target Identification**: Carefully distinguish between the subject of the passage and the target of the question. If the question asks for a location associated with an institution, return the location, not the institution itself.

## Execution Strategy
1. **Parse & Isolate**: Strip conversational framing. Identify the core query type (entity, location, date, role).
2. **Scan & Match**: Locate verbatim or near-verbatim matches in `[DOC]`/`[PAR]` blocks. Prioritize passages where the clue aligns with the answer.
3. **Cross-Snippet Validation**: When multiple passages discuss the same topic or reference multiple items, scan all snippets to find the common thread or connecting entity. Cross-reference details to ensure consistency.
4. **Verify Granularity**: Check if the extracted span matches the exact length, number, and specificity of the expected answer. Adjust if the context provides a more precise term.
5. **Grounding Constraint**: Only extract answers explicitly stated or strongly implied in the provided context. Avoid external knowledge substitution, guessing, or substituting similar concepts.
6. **Format Output**: Provide reasoning outside tags. Enclose only the final concise answer in `<answer>...</answer>`.
