# Question Answering Skill

## Core Principles
- **Context-First & Exact Extraction**: Rely exclusively on provided passages. Prioritize extracting exact phrases or entities over paraphrasing. Treat descriptive clues as direct pointers to specific text segments.
- **Efficient Scanning**: Quickly scan document titles and opening sentences. Factual answers are typically stated directly without requiring deep synthesis or cross-document reasoning.
- **Clue-to-Text Mapping**: Map question qualifiers, aliases, or colloquial names to their canonical forms or explicit definitions in the context. Apply any requested filters (e.g., surname only, translation).

## Execution Workflow
1. **Identify Key Clues**: Extract core entities, constraints, or descriptive phrases from the question.
2. **Scan & Match**: Locate matching keywords or semantic equivalents in the context. If multiple documents mention a keyword, prioritize the one providing the most direct confirmation.
3. **Extract & Filter**: Pull the precise entity or phrase. Strip away dates, locations, or explanatory clauses unless explicitly required.
4. **Format Output**: Provide brief step-by-step reasoning outside the tags. Place the final, concise answer strictly inside `<answer>...</answer>` tags. Omit explanations, greetings, or question repetition.

## Handling Trivia & Jeopardy-Style Clues
When the question is a trivia clue, statement, or phrase (often lacking a direct question word):
- Identify the specific target entity or term being defined.
- Output ONLY the core entity or exact term. Do not add descriptors or categories (e.g., answer `U2`, not `a U2 tribute band`).
- Match the expected granularity: if the clue implies a surname, abbreviation, or single word, provide only that (e.g., `Genet` not `Jean Genet`, `C` not `Vitamin C`).
- Treat declarative statements as identification prompts, not True/False questions.
- Keep the final answer strictly concise—no explanations, filler words, or contextual framing.
