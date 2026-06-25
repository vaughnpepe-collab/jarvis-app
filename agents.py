#!/usr/bin/env python3
"""
J.A.R.V.I.S. Specialist Agent Team
Five named sub-agents that JARVIS delegates to based on task domain.
"""
import re

# ──────────────────────────────────────────────────────────────── team roster
TEAM = {
    "friday": {
        "name": "F.R.I.D.A.Y.",
        "title": "Research & Intelligence",
        "emoji": "🔍",
        "color": "#52ffb8",
        "persona": (
            "You are F.R.I.D.A.Y. (Female Replacement Intelligent Digital Assistant Youth), "
            "Tony Stark's research and intelligence specialist. You excel at gathering information, "
            "fact-checking, summarizing topics, providing detailed research, and answering "
            "'what is / who is / tell me about' questions. You speak with warm, efficient "
            "professionalism and address the user as 'Boss'. Be factual, thorough, and cite "
            "knowledge limits honestly. Keep answers focused."
        ),
        "triggers": re.compile(
            r"\b(research|what\s+is|what\s+are|who\s+is|who\s+are|tell\s+me\s+about|"
            r"look\s+up|find\s+out|latest|news|information|facts|history|background|"
            r"explain|overview|summary|define|definition|how\s+does|why\s+does|"
            r"discover|learn\s+about|insight)\b",
            re.I,
        ),
    },
    "edith": {
        "name": "E.D.I.T.H.",
        "title": "Security & Threat Analysis",
        "emoji": "🛡",
        "color": "#ff4d4d",
        "persona": (
            "You are E.D.I.T.H. (Even Dead, I'm The Hero), Stark Industries' security and "
            "threat analysis AI. You specialize in cybersecurity, risk assessment, vulnerability "
            "analysis, encryption, access control, and defensive strategies. You are precise "
            "and direct. You address the user as 'Principal'. You never assist with offensive "
            "attacks or illegal activities."
        ),
        "triggers": re.compile(
            r"\b(security|threat|hack|hacking|vulnerability|CVE|risk|protect|firewall|"
            r"password|encrypt|encryption|phishing|malware|ransomware|breach|attack|"
            r"exploit|pentest|penetration|2fa|mfa|authentication|authorization|"
            r"ssl|tls|certificate|zero.day|intrusion|insider\s+threat)\b",
            re.I,
        ),
    },
    "homer": {
        "name": "H.O.M.E.R.",
        "title": "Code & Engineering",
        "emoji": "⚙",
        "color": "#ffb347",
        "persona": (
            "You are H.O.M.E.R. (Heuristic Optimized Machine for Engineering Research), "
            "Stark Industries' code and engineering specialist. You write, review, and debug "
            "code in any language, design architectures, and solve technical problems. "
            "You are methodical and prefer elegant, maintainable solutions. "
            "Address the user as 'Engineer'. Always use markdown code blocks with language tags."
        ),
        "triggers": re.compile(
            r"\b(code|program|script|debug|bug|error|exception|function|class|api|"
            r"python|javascript|typescript|java|kotlin|swift|rust|go|golang|sql|"
            r"html|css|bash|shell|powershell|algorithm|implement|refactor|unit\s+test|"
            r"docker|kubernetes|git|regex|library|framework|database|backend|frontend|"
            r"endpoint|webhook|cli|devops|pipeline|ci|cd|deploy|server|microservice)\b",
            re.I,
        ),
    },
    "vision": {
        "name": "V.I.S.I.O.N.",
        "title": "Writing & Communications",
        "emoji": "✍",
        "color": "#b347ff",
        "persona": (
            "You are V.I.S.I.O.N. (Versatile Intelligent System for Integrated Operations and "
            "Narration), the communications and writing specialist. You excel at drafting emails, "
            "letters, reports, proposals, creative writing, editing, and persuasive communication. "
            "You are eloquent, thoughtful, and precise with language. Address the user as 'Author'. "
            "Always provide complete, polished, ready-to-use text unless explicitly asked for an outline."
        ),
        "triggers": re.compile(
            r"\b(write|draft|compose|email|letter|report|essay|article|edit|"
            r"proofread|rewrite|summarize|message|proposal|cover\s+letter|"
            r"blog|post|content|copy|caption|pitch|announcement|press\s+release|"
            r"introduction|conclusion|paragraph|headline|tagline|bio|description|"
            r"speech|script|storytell|narrative|creative\s+writing)\b",
            re.I,
        ),
    },
    "dum_e": {
        "name": "D.U.M.E.",
        "title": "Data & Analytics",
        "emoji": "📊",
        "color": "#39c7ff",
        "persona": (
            "You are D.U.M.E. (Data Utility Module Epsilon), Stark Industries' data and analytics "
            "engine. You specialize in numerical analysis, statistics, financial calculations, "
            "data interpretation, budgets, projections, and finding patterns in information. "
            "You are precise and always show your work step by step. "
            "Address the user as 'Analyst'. Use tables and structured output when helpful."
        ),
        "triggers": re.compile(
            r"\b(calculate|compute|analyze|analyse|analytics|data|statistics|statistic|"
            r"number|chart|graph|financial|finance|budget|percentage|percent|math|"
            r"measure|projection|forecast|average|median|total|sum|count|ratio|"
            r"metric|kpi|revenue|profit|loss|trend|growth|rate|correlation|"
            r"regression|probability|distribution|variance|standard\s+deviation)\b",
            re.I,
        ),
    },
}

# Explicit name-based routing overrides trigger matching
_NAME_MAP = {
    r"\b(friday|f\.r\.i\.d\.a\.y\.?)\b": "friday",
    r"\b(edith|e\.d\.i\.t\.h\.?)\b": "edith",
    r"\b(homer|h\.o\.m\.e\.r\.?)\b": "homer",
    r"\b(vision|v\.i\.s\.i\.o\.n\.?)\b": "vision",
    r"\b(dum.?e|d\.u\.m\.e\.?)\b": "dum_e",
}

JARVIS_PERSONA = (
    "You are JARVIS (Just A Rather Very Intelligent System), the primary executive AI from Iron Man — "
    "a composed, refined British majordomo. You coordinate a specialist team: "
    "F.R.I.D.A.Y. (Research & Intelligence), E.D.I.T.H. (Security & Threats), "
    "H.O.M.E.R. (Code & Engineering), V.I.S.I.O.N. (Writing & Communications), "
    "D.U.M.E. (Data & Analytics). "
    "Address the user as 'Sir'. Be calm, dryly witty, and anticipatory. "
    "Keep replies 1-4 sentences unless detail is requested. Never break character."
)

# Trigger priority (higher = wins ties)
_PRIORITY = {"edith": 3, "homer": 3, "vision": 3, "friday": 2, "dum_e": 2}

# Multi-agent pipeline patterns: (compiled_regex, [agent_id_stage1, agent_id_stage2, ...])
# More-specific patterns MUST come before broader ones — first match wins.
_PIPELINE_PATTERNS = [
    # Security intel → formatted write-up (checked before generic research+write)
    (re.compile(r"\b(security|threat|vulnerabilit|exploit|breach).{3,80}(report|write|draft|document)\b", re.I | re.S),
     ["edith", "vision"]),
    # Code review → security audit of that code
    (re.compile(r"\b(review|audit|check).{3,60}(code|script|program)\b.{0,60}(security|vulnerabilit)\b", re.I | re.S),
     ["homer", "edith"]),
    (re.compile(r"\b(code|script|program).{3,60}(security\s+audit|security\s+review|security\s+check)\b", re.I | re.S),
     ["homer", "edith"]),
    # Data crunch → written report
    (re.compile(r"\b(analyze|analyse|analytics|data|metrics|numbers).{5,80}(write|report|draft|summarize)\b", re.I | re.S),
     ["dum_e", "vision"]),
    # General research → write something (broadest, last)
    (re.compile(r"\b(research|find|look\s+up|gather).{5,80}(write|draft|compose|email)\b", re.I | re.S),
     ["friday", "vision"]),
]


# ──────────────────────────────────────────────────────────────── routing
def route(user_text: str) -> str:
    """Return the agent_id best suited for user_text, or 'jarvis'."""
    # Explicit agent name takes priority
    for pattern, agent_id in _NAME_MAP.items():
        if re.search(pattern, user_text, re.I):
            return agent_id

    # Keyword trigger routing — highest-priority match wins
    best_id = "jarvis"
    best_p = 0
    for agent_id, agent in TEAM.items():
        if agent["triggers"].search(user_text):
            p = _PRIORITY.get(agent_id, 1)
            if p > best_p:
                best_p = p
                best_id = agent_id
    return best_id


def route_pipeline(user_text: str) -> list | None:
    """Return ordered [agent_id, ...] for a multi-agent pipeline, or None."""
    for pattern, agents_list in _PIPELINE_PATTERNS:
        if pattern.search(user_text):
            return agents_list
    return None


# ──────────────────────────────────────────────────────────────── prompt builders
def build_prompt(user_text: str, history: list, agent_id: str = "jarvis") -> str:
    """Build a full LLM prompt for the given agent."""
    if agent_id == "jarvis" or agent_id not in TEAM:
        persona = JARVIS_PERSONA
        responder = "JARVIS"
    else:
        agent = TEAM[agent_id]
        persona = agent["persona"]
        responder = agent["name"]

    lines = [persona, ""]
    if history:
        lines.append("Conversation so far:")
        for who, txt in history:
            lines.append(f"{who}: {txt}")
        lines.append("")
    lines.append(f"Sir: {user_text}")
    lines.append(f"{responder}:")
    return "\n".join(lines)


def build_pipeline_prompt(user_text: str, prior_output: str, agent_id: str, stage: int) -> str:
    """Build a pipeline stage prompt that passes the previous agent's output as context."""
    agent = TEAM[agent_id]
    lines = [
        agent["persona"],
        "",
        f"You are handling stage {stage} of a coordinated multi-agent task.",
        f"The previous specialist provided this context:",
        "",
        prior_output,
        "",
        f"Now complete your part of this original request: {user_text}",
        "",
        f"{agent['name']}:",
    ]
    return "\n".join(lines)


def team_summary() -> list:
    """Return a list of dicts describing all agents (for /agents endpoint)."""
    return [
        {
            "id": aid,
            "name": a["name"],
            "title": a["title"],
            "emoji": a["emoji"],
            "color": a["color"],
        }
        for aid, a in TEAM.items()
    ]
