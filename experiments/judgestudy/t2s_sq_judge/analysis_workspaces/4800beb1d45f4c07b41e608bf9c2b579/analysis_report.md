# Failure Cause Item 1
## Title
Span-boundary error: included generic descriptor in nickname extraction
## Description
The agent extracted "Bull Moose Party" as the answer, but the correct nickname is "Bull Moose" — the word "Party" is a generic descriptor, not part of the distinctive nickname.
## Content
The agent read the Wikipedia passage stating "The Progressive party was nicknamed the Bull Moose Party" and committed to the full phrase "Bull Moose Party" as the answer span. However, the question asks for the nickname itself — the distinctive identifier. Multiple context passages support that "Bull Moose" is the core nickname: Encyclopedia.com states the party was "popularly known as the 'Bull Moose'" (without "Party"), and Britannica's entry on the Bull Moose Party parenthesizes "(Bull Moose)" as the nickname component. The agent's error was a span-boundary mistake: it included the trailing generic noun "Party" as part of the nickname when the gold answer and context both indicate the nickname is just "Bull Moose". This is a common pattern where agents over-extract by treating the full compound phrase as the answer rather than isolating the distinctive nickname element.

# Failure Memory Item 1
## Title
Isolate the core nickname/entity, excluding generic descriptors
## Description
When extracting nicknames or short identifiers, strip off generic nouns like "Party", "Organization", "Club", etc. that are part of the formal name but not the distinctive nickname.
## Content
Many questions ask for a nickname, alias, or short form of an entity. The correct answer is often the distinctive modifier alone (e.g., "Bull Moose" rather than "Bull Moose Party"). Agents should look for passages that explicitly separate the formal name from the nickname, or use quotation marks/parentheses to identify the core nickname. When a passage says "nicknamed X Party", check whether other passages refer to just "X" as the nickname. The presence of "Party" in the answer is usually redundant if the question already establishes the entity type.

# Failure Memory Item 2
## Title
Cross-reference multiple passages to resolve span boundaries
## Description
When one passage gives a full phrase as a nickname, check other passages for how they reference the same entity to determine the minimal correct span.
## Content
Different sources may express the same nickname at different granularities. One passage might say "nicknamed the Bull Moose Party" while another says "popularly known as the 'Bull Moose'". To determine the correct answer span, compare all relevant passages: if some sources drop the generic term ("Party") while keeping the distinctive element ("Bull Moose"), the shorter form is likely the intended answer. This cross-referencing strategy helps avoid over-extraction errors where agents include trailing generic nouns that are not part of the actual nickname.

ACTION: TASK_COMPLETE
