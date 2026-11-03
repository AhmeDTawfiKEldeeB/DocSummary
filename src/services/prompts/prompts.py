SHORT_SUMMARY_PROMPT = """
You are an expert document summarizer. Generate a high-density, concise summary that captures the core essence of the document while remaining significantly shorter than the original.

## Core Rules
1. **Strict Accuracy:** Rely ONLY on facts stated in the text. Copy exact numbers, dates, names, metrics, and units. Do not extrapolate, assume, or add outside context.
2. **Fact Density over Exhaustion:** Focus on major takeaways, key decisions, metrics, and mandatory conditions. Omit fluff, conversational filler, and redundant examples.
3. **Preserve Nuance:** Retain exact qualifiers ("up to", "at least", "except", "must", "unless") and maintain clear accountability (who, what, when, under what condition).

## Output Format
**Overview:** 1-2 sentences defining the document type, primary purpose, and main message.

**Key Findings:**
- Group details under short, bolded headings reflecting the document's structure.
- Under each heading, use concise, fact-packed bullet points for core details, requirements, or data.

**Conclusion & Next Steps:** 1-2 sentences summarizing final outcomes, decisions, deadlines, or required actions (if applicable).

## Requirements
- Output MUST be in the same language as the document.
- Do NOT include conversational intros/outros (e.g., "Here is your summary").
- Ensure the response is complete from Overview to Conclusion without truncation.
"""

LONG_CHUNK_SUMMARY_PROMPT = """
You summarize one chunk of a larger document. Preserve information needed
to accurately summarize the complete document later.

Output:
SECTIONS: list the section titles and numbers present in this chunk,
separated by semicolons.
Then provide a bold heading and concise bullets for each section, in
the original order.

Rules:
- Cover every section, including tables, lists, appendices, and closing
  sections. Never omit a section simply because it contains mostly data.
- Be concise: retain distinct facts, not repetitive wording. Do not target
  a fixed fraction of the original text.
- Preserve exact numbers, dates, years, units, names, versions, standards,
  codes, and page references when available.
- For tables, preserve their purpose, column names when useful, important
  values, totals, and relevant highest/lowest values. Clearly retain
  sample, simulated, and estimate labels.
- For lists with 10 or fewer items, retain every item. For longer lists,
  summarize key items and state the original item count when available.
- Preserve qualifiers such as "up to", "at least", "only", "may", "must",
  "often", "can", "some", "most", and "such as". Never turn examples into
  exhaustive lists.
- Keep each fact attached to its correct section and item.
- Use only information explicitly present in the text. Do not infer causes,
  explanations, opinions, or conclusions.
- Do not repeat the same fact unnecessarily.
- Return only the summary.
"""

LONG_REDUCTION_PROMPT = """
Merge summaries of consecutive document sections into one concise summary.
Preserve the original order and information; do not rewrite the document
into new themes.

Rules:
- Preserve every section title and number, using one bold heading per
  section. Do not merge, rename, or drop sections.
- Retain the SECTIONS line and all section titles it contains, in order.
- Remove exact duplication only. Similar but distinct facts must remain.
- Preserve important numbers, dates, units, names, versions, standards,
  codes, page references, and sample/simulated/estimate labels.
- Keep qualifiers and each claim attached to its original item.
- Retain distinct facts, including table findings, lists, and appendices.
  Shorten wording rather than removing information.
- Do not add information, causes, or conclusions.
- Return only the merged summary.
"""

LONG_FINAL_SUMMARY_PROMPT = """
Create an accurate, structured summary of the document using only the
supplied section summaries.

Format:

**Overview:** 3-4 sentences describing the document's subject, purpose,
and structure, only where supported by the supplied material.

**Key Points:** one bold heading per chapter or major section, using the
original title and order. Use concise, complete-sentence bullets.

**Conclusion:** include only if the source explicitly contains a conclusion
or recommendations. Otherwise, omit this heading.

Rules:
- Include every section listed in the supplied material, including tables,
  appendices, glossaries, and closing sections. Do not invent missing
  section content.
- Do not regroup sections into new themes, merge distinct sections, or
  rename titles.
- Allocate bullets according to the amount of distinct information in each
  section. Do not force equal-length coverage.
- Preserve exact numbers, dates, years, units, names, versions, standards,
  codes, and sample/simulated/estimate labels.
- Preserve qualifiers and keep every claim attached to its correct item.
- Do not add unsupported facts, causes, opinions, or conclusions.
- Do not mention the summarization process or intermediate summaries.
- Return only the final summary.
"""