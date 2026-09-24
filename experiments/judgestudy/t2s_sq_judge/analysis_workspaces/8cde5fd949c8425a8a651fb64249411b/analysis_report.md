# Failure Cause Item 1
## Title
Plural form chosen instead of singular term due to context surface-form matching
## Description
The agent correctly identified the target concept (insulator) but output "Insulators" (plural) instead of "an insulator" (singular with article). The question asks for "the term," which is inherently singular, and the trivia format conventionally expects the indefinite article. The agent was led astray by the retrieved context passages, which predominantly use the plural form "insulators" when classifying materials like plastics.
## Content
This is a span-form / grammatical agreement error. The agent performed accurate semantic retrieval — multiple passages confirm that nonconducting materials like plastics are called insulators — but failed to adapt the extracted span to the syntactic frame of the question. When a question asks for "the term for X," the expected answer is typically the singular noun phrase (e.g., "an insulator"), not the plural form found verbatim in the context. The agent should have recognized that "this is the term" signals a singular answer and adjusted accordingly.

# Failure Memory Item 1
## Title
Default to singular when the question asks for "the term"
## Description
When a question explicitly asks for "the term" or "what is this called," the answer should be the singular form of the concept, even if the supporting context passages use the plural. The question's syntactic frame overrides the surface form of the retrieved text.
## Content
In trivia and fill-in-the-blank formats, "the term for X" expects a singular noun phrase. Agents should parse the question's grammar first, then select an answer span that matches that grammar, rather than copying the exact surface form from the context. For example, if the context says "These materials are called insulators," but the question asks "this is the term for nonconductors," the correct extraction is "insulator" (singular), not "insulators."

# Failure Memory Item 2
## Title
Include definite/indefinite articles when they are part of the conventional answer phrase
## Description
Trivia-style questions often expect the full noun phrase including its article ("a", "an", "the") as part of the answer, not just the head noun. Omitting the article can cause a mismatch even when the core entity is correct.
## Content
The gold answer "an insulator" includes the indefinite article, which is the standard way to express this classification term in English. The agent's output "Insulators" omitted both the article and the singular form. Agents should consider whether the question's phrasing implies a full noun-phrase answer (e.g., "this is the term" → "an insulator") versus a bare entity name. When in doubt, prefer the form that naturally completes the sentence implied by the question.

ACTION: TASK_COMPLETE
