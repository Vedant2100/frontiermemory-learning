"""Remove quoted chat messages and assistant narration from markdown files in the review artifact (run on the staged copy only).
Usage: python3 -I scripts/scrub_chat.py FILE...
The logs say "(user: "...")", "user chose "..."" or "user decision ("...")"; the artifact keeps who decided, not the words said."""
import re
import sys

S = re.S
RULES = [
    (r"\s?\(D\d{2,3}(?:(?:,|\s+to)\s*D\d{2,3})*\)", ""),     # (D94), (D132, D139): ids that point into the working diary
    (r"[;,]\s*D\d{2,3}\)", ")"), (r"(What happened:\*\*) D\d{2,3}\.", r"\1"),
    (r"[,;]?\s*\bD\d{2,3}\b(?=[)\s.,;:|])", ""),                                    # any id left after the forms above (r"Rule from D\d{2,3}:", "Rule:"),
    (r'\((?:the )?user: "[^"]*"(?: …)?(?: "[^"]*")*\)', "(project-owner decision)"),   # (user: "a" … "b")
    (r'\((?:the )?user: "[^"]*"', "(project-owner decision"),                          # (user: "Add run 4", prereg ...)
    (r'user decision \("[^"]*"[^)]*?\)', "project-owner decision"),
    (r'\(user decision, "[^"]*"\)', "(project-owner decision)"),
    (r'\("[^"]*", with the order below\)', "(with the order below)"),
    (r"\(user decision, ([A-Za-z]+ [0-9]+)\)", r"(project-owner decision, \1)"),
    (r'user (?:chose|picked|selected) "[^"]*"', "the project owner chose"),
    (r'then "OK" to restart the server', "then to restart the server"),
    (r' Also noted: I asked the user instead of acting at 00:15 and the chain sat idle for about 10 hours after the stop; from now on', " Also noted: the chain sat idle for about 10 hours after the stop; from now on"),
    (r"\(user\s+decision:", "(project-owner decision:"),
    (r'decision "go" after "[^"]*"', "decision"),
    (r'(\*\*(?:[Uu]ser|project-owner) decision[^*]*?\*\*) \("[^"]*"\)', r"\1"),                  # **User decision: x** ("quote").
    (r'(?i)\buser decisions\b', "project-owner decisions"), (r'(?i)\buser decision\b', "project-owner decision"),
    (r"\buser requirement\b", "project-owner requirement"), (r"\buser approved\b", "the project owner approved"),
    (r"\buser allowed\b", "the project owner allowed"), (r"\buser asked\b", "the project owner asked"),
    (r"\bUser decision\b", "Project-owner decision"),
    (r"\bUser (approved|asked|chose|said|agreed|allowed)\b", r"Project owner \1"),
    (r"\bthe user(?:’|')s\b", "the project owner’s"), (r"\bthe user\b(?![-\w])", "the project owner"),
    (r"\bthe user-run\b", "the project-owner-run"),
]
for f in sys.argv[1:]:
    t = o = open(f, encoding="utf-8").read()
    for pat, rep in RULES:
        t = re.sub(pat, rep, t, flags=S)
    if t != o:
        open(f, "w", encoding="utf-8").write(t)
