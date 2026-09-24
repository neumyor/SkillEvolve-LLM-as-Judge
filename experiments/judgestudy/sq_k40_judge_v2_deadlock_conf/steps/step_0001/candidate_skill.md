# Question Answering Skill

# Answer Precision & Format Rules
- **Exact Match Priority**: Return exactly the target word or phrase. Do not add descriptors, titles, or explanations (e.g., use 'C' not 'Vitamin C', 'Genet' not 'Jean Genet', 'U2' not 'U2 tribute band').
- **Minimal Output**: Keep answers to the absolute minimum required. Single-word answers should never be expanded into phrases.
- **Clue Interpretation**: Questions may be trivia clues or sentence fragments. Identify the specific missing entity or term that completes the clue. Do not answer with 'Yes/No' or conversational filler unless explicitly asked.

## Execution Strategy
1. **Parse Clues**: Isolate key identifiers (names, roles, locations, quoted strings) in the question.
2. **Scan & Match**: Locate these identifiers in the `[DOC]`/`[PAR]` blocks. Prioritize passages where the clue appears verbatim or with minimal paraphrasing. Cross-check details across overlapping snippets to confirm the correct entity.
3. **Extract & Verify**: Pull the precise answer span. Validate against all provided snippets to avoid hallucination or mismatched entities. Use internal knowledge only as secondary validation.
4. **Format Output**: Provide a brief step-by-step rationale if helpful, but strictly enclose the final concise answer within `<answer>...</answer>` tags. Do not repeat the question or add filler.

## Grounding Constraint
- Only extract answers directly stated or strongly implied in the provided context. Do not guess or substitute similar concepts (e.g., do not guess 'swimming pool' if 'well' is the intended answer).
