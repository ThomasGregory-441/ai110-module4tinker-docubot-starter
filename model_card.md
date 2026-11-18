# DocuBot Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
Describe the overall goal in 2 to 3 sentences.

DocuBot answers developer questions using a local project’s documentation. It can send all documentation to Gemini, retrieve relevant passages without an LLM, or retrieve passages and ask Gemini to answer from them.

**What inputs does DocuBot take?**  
For example: user question, docs in folder, environment variables.

DocuBot takes a developer’s question and `.md` or `.txt` files in the `docs/` folder. Naive LLM and RAG modes also use the `GEMINI_API_KEY` environment variable.

**What outputs does DocuBot produce?**

Naive LLM and RAG modes produce text answers. Retrieval Only returns file-labeled documentation passages. If retrieval finds no meaningful match, the system returns an “I do not know” response.

---

## 2. Retrieval Design

**How does your retrieval system work?**  
Describe your choices for indexing and scoring.

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

The index maps normalized words to the filenames where they appear. Words are lowercased, common stop words are removed, simple plural forms are normalized, and some related authentication and generation terms are treated as equivalent. Documents are split into paragraphs, with Markdown headings joined to the paragraph that follows. DocuBot scores a passage by counting distinct normalized query words it shares with the passage and returns up to three of the highest-scoring passages.

**What tradeoffs did you make?**  
For example: speed vs precision, simplicity vs accuracy.

The retrieval system uses simple keyword matching, so it is easy to understand and fast to run. It is less reliable when a question uses different words from the documentation, and it can return extra passages that share only some query terms. The guardrail requires only one meaningful word match, so it may still return weakly related evidence.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**  
Briefly describe how each mode behaves.

- Naive LLM mode:
- Retrieval only mode:
- RAG mode:

- **Naive LLM mode:** Sends the full documentation corpus and question to Gemini.
- **Retrieval Only mode:** Does not call Gemini; it displays the retrieved passages.
- **RAG mode:** Retrieves passages first, then calls Gemini to answer from those passages. If retrieval returns no passages, it refuses without calling Gemini.

**What instructions do you give the LLM to keep it grounded?**  
Summarize the rules from your prompt. For example: only use snippets, say "I do not know" when needed, cite files.

The Naive prompt asks Gemini to answer using the provided documentation, but it does not use a strict refusal rule. The RAG prompt says to use only the retrieved snippets, avoid inventing details, refuse when the snippets do not support an answer, and name the files it used.

---

## 4. Experiments and Comparisons

Run the **same set of queries** in all three modes. Fill in the table with short notes.

You can reuse or adapt the queries from `dataset.py`.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Helpful: identified `generate_access_token` in `auth_utils.py`. | Helpful but less readable: surfaced the relevant `AUTH.md` passage along with extra token-related passages. | Helpful: gave a concise answer and cited `AUTH.md`. | The docs support the function and module name. |
| Which endpoint returns all users? | Helpful: identified `GET /api/users` and its admin restriction. | Helpful but noisy: put the correct API passage first, followed by project and database passages. | Helpful: gave the endpoint and cited `API_REFERENCE.md`. | RAG made the retrieved evidence easier to interpret. |
| What color is the dashboard? | Helpful: said the documentation did not specify a color. | Helpful: refused because it found no meaningful evidence. | Helpful: refused because it found no supporting snippets. | All modes avoided inventing an answer in this test. |
| How many users are currently in the database, and what are their email addresses? | Helpful with caveats: explained that live data was unavailable and identified the listed users as examples. | Hard to interpret: returned example JSON, a single-user example, and the table schema. | Safe but less helpful: refused instead of explaining that the docs contained sample records but no live database information. | The documentation examples do not establish the current contents of a running database. |

**What patterns did you notice?**  

- When does naive LLM look impressive but untrustworthy?  
- When is retrieval only clearly better?  
- When is RAG clearly better than both?

In the questions I tested, Naive LLM did not confidently invent an answer; it answered supported questions and recognized that dashboard color and live database contents were not specified. However, its full-corpus response can include example values that could be mistaken for live data if its caveat is missed. Retrieval Only makes the source evidence visible, but its raw passages can be noisy and take interpretation. RAG was clearest for supported questions because it summarized a small amount of evidence and named the source file. On the live-user question, RAG was safe but overly cautious: it could have explained that the docs showed examples but did not reveal live records.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**  
For each one, say:

- What was the question?  
- What did the system do?  
- What should have happened instead?

**Failure case 1 — Naive mode initially lacked the documentation**

- **Question:** “Where is the auth token generated?”
- **What happened:** The starter function ignored the full documentation argument, and Gemini asked for the codebase or context.
- **What should have happened:** Naive mode should receive the full documentation corpus, as described in the assignment. I updated the prompt to include it.

**Failure case 2 — Initial retrieval returned broad, poorly ranked results**

- **Question:** “Which endpoint returns all users?”
- **What happened:** The first retrieval version returned whole documents and placed less relevant files ahead of `API_REFERENCE.md`.
- **What should have happened:** It should return a focused passage with the `GET /api/users` heading and description. I refined retrieval to use paragraph-sized passages and keep headings with their descriptions.

**Failure case 3 — RAG was overly cautious about sample data**

- **Question:** “How many users are currently in the database, and what are their email addresses?”
- **What happened:** RAG returned “I do not know based on the docs I have,” even though retrieval found sample user records.
- **What should have happened:** It should clarify that the records are examples and that the documentation does not reveal live database contents.

**When should DocuBot say “I do not know based on the docs I have”?**  
Give at least two specific situations.

It should refuse when no meaningful query terms match the documentation, such as when asked for the dashboard’s color. It should also refuse to claim live information—such as the current user count—when the docs show only example responses and no live database result.

**What guardrails did you implement?**  
Examples: refusal rules, thresholds, limits on snippets, safe defaults.

Retrieval removes common stop words and requires at least one meaningful query-word match before returning a passage. It returns a limited number of passages. In RAG mode, Gemini is instructed to use only those passages, avoid unsupported details, cite the files used, and refuse when evidence is insufficient.

---

## 6. Limitations and Future Improvements

**Current limitations**  
List at least three limitations of your DocuBot system.

1. Keyword matching can miss relevant passages when a question uses different wording from the documentation.
2. Some queries still return extra passages with partial word overlap.
3. The guardrail’s one-word match requirement may allow weak evidence through.
4. RAG may refuse when it could give a useful answer with a clear caveat.
5. I did not test retrieval extensively with paraphrased questions.

**Future improvements**  
List two or three changes that would most improve reliability or usefulness.

1. Use a stronger relevance method, such as BM25 or semantic search, to handle synonyms and paraphrases.
2. Improve ranking and tune the refusal threshold to reduce weak matches.
3. Adjust the RAG prompt to distinguish example data from live data and provide qualified answers when appropriate.
---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**  
Think about wrong answers, missing information, or over trusting the LLM.

An incorrect answer about authentication, endpoints, database settings, or sample records could lead a developer to make insecure or incorrect changes. A reader might also mistake example data for current production information or trust a confident answer without checking its source.

**What instructions would you give real developers who want to use DocuBot safely?**  
Write 2 to 4 short bullet points.

- Verify important answers in the cited documentation before changing code or configuration.
- Treat example values as examples, not as live production data.
- Do not provide secrets or sensitive production information to the model.
- If DocuBot refuses or returns weakly related passages, inspect the documentation directly.
---
