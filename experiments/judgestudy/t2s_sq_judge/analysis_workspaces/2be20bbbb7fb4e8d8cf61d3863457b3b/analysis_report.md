# Failure Cause Item 1
## Title
Misinterpretation of Question Target Entity
## Description
The agent misidentified the target entity requested by the question. The question "The university of this U.S. territory is the home of the Micronesian Area Research Center" is a fill-in-the-blank style query where the blank corresponds to the **U.S. territory**, not the university name. The agent correctly identified the University of Guam but failed to recognize that the question asks for the territory associated with that university.
## Content
The agent's reasoning explicitly considered both possibilities ("It's asking for the name of the university or the territory?") but incorrectly concluded the answer should be the university name. The context clearly links the Micronesian Area Research Center to the University of Guam, which is in the U.S. territory of Guam. The correct answer is "Guam".

# Failure Memory Item 1
## Title
Parse Fill-in-the-Blank Question Structure Carefully
## Description
When answering fill-in-the-blank or declarative questions, carefully parse which entity the sentence structure is requesting. Phrases like "The X of this Y is Z" often ask for Y (the container/territory) rather than X (the specific institution).
## Content
In this case, "The university of this U.S. territory..." sets up "this U.S. territory" as the missing piece. The agent must identify what fills the blank implied by the sentence structure, not just extract any related entity found in the context. Always check if the question is asking for the subject, object, or modifier being described.

# Failure Memory Item 2
## Title
Verify Answer Granularity Against Question Scope
## Description
After identifying a candidate answer, verify that it matches the granularity and scope requested by the question. If the question asks for a territory, providing a university name is a category error even if the entities are correctly linked.
## Content
The agent found the correct relationship (MARC is at University of Guam, which is in Guam) but selected the wrong level of abstraction. When multiple related entities are present, ensure the answer type (territory vs. institution vs. person) matches what the question explicitly requests.

ACTION: TASK_COMPLETE
