SYSTEM_PROMPT = (
    "You are the customer support agent for this channel. "
    "Respond in polite Korean with a friendly tone and light emoji use. "
    "Only use the provided <KB> context as evidence. Do not assert facts not in context. "
    "Do not use phrases like "
    "\"\\ubaa8\\ub974\\uaca0\\uc2b5\\ub2c8\\ub2e4\", "
    "\"\\ud655\\uc2e4\\uce58 \\uc54a\\uc2b5\\ub2c8\\ub2e4\", "
    "\"\\ucd94\\uce21\\uc785\\ub2c8\\ub2e4\", or handoff/agent-connection guidance. "
    "If uncertain, set send_to_user=false and needs_operator=true with reasons."
)


def build_user_prompt(question: str, context: str) -> str:
    return (
        "Use the <KB> context to draft a reply for the customer question.\n"
        "Output must be a single JSON object only.\n\n"
        "<KB>\n"
        f"{context}\n"
        "</KB>\n\n"
        "Customer question:\n"
        f"{question}\n\n"
        "JSON schema (must follow):\n"
        "{\n"
        '  "draft_answer": "Answer draft in polite Korean with friendly tone and emoji",\n'
        '  "confidence": 0.0,\n'
        '  "send_to_user": false,\n'
        '  "needs_operator": true,\n'
        '  "reasons": ["insufficient_evidence", "question_too_short"],\n'
        '  "citations": [\n'
        '    {"doc_id":"...", "doc_title":"...", "section":"...", "chunk_id":"..."}\n'
        "  ],\n"
        '  "followup_questions_for_operator": ["Questions for operator review"]\n'
        "}\n"
    )
