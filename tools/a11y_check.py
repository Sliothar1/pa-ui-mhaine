#!/usr/bin/env python3
"""Static accessibility gate (stdlib only). Usage: python3 a11y_check.py CONFIG.json [--report out.json]

Checks, per the 2026-10-11 reviews:
  C1 computed WCAG contrast of every accent/text token against every surface token, per theme
     (AA: 4.5:1 for text tokens, 3:1 for tokens declared `ui` = non-text/large only)
  C2 skip link: first link in <body> is href="#id" and that id exists
  C3 prefers-reduced-motion: if any CSS uses transition/animation, a reduced-motion media query exists;
     JS that animates (flyTo/animate/requestAnimationFrame/scrollIntoView smooth) must consult it (warn)
  C4 <html lang="en"> present
  C5 lang="ga" heuristic: text outside a lang="ga" ancestor that looks Irish (fada words, lenited
     Mh/Bh/Dh/Fh/Gh/Ch... initials, eclipsis like nGaillimh) and is not on the allowlist -> WARN
  C6 non-map list view: each page with a map container names a list/table equivalent (config `map_pages`)
Exit 1 on any FAIL; WARNs never fail.
"""
import json, os, re, sys
from html.parser import HTMLParser

HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def lum(hexc):
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def theme_tokens(css, selectors):
    """{theme: {token: value}}; later themes inherit from the first (base) one."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = {}
    base = None
    for name, sel in selectors.items():
        toks = {}
        for m in re.finditer(re.escape(sel) + r"\s*\{([^}]*)\}", css):
            for k, v in re.findall(r"--([\w-]+)\s*:\s*([^;]+)", m.group(1)):
                toks[k] = v.strip()
        merged = dict(out[base]) if base else {}
        merged.update(toks)
        out[name] = merged
        base = base or name
    for t in out.values():  # resolve var()
        for _ in range(5):
            for k, v in list(t.items()):
                m = re.fullmatch(r"var\(--([\w-]+)(?:,[^)]*)?\)", v)
                if m and m.group(1) in t:
                    t[k] = t[m.group(1)]
    return out


class Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_lang = None; self.ids = set(); self.first_link = None; self.in_body = False
        self.stack = []; self.texts = []; self.skip_depth = 0; self.classes = set(); self.tags = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.add(tag)
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "body":
            self.in_body = True
        if a.get("id"):
            self.ids.add(a["id"])
        for c in (a.get("class") or "").split():
            self.classes.add(c)
        if tag == "a" and self.in_body and self.first_link is None:
            self.first_link = a.get("href")
        if tag in self.VOID:
            return
        lang = a.get("lang")
        parent = self.stack[-1][1] if self.stack else None
        hidden = tag in ("script", "style", "svg", "noscript", "code", "pre") or a.get("translate") == "no"
        self.stack.append((tag, lang or parent, hidden or (self.stack[-1][2] if self.stack else False)))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.in_body or not data.strip():
            return
        lang = self.stack[-1][1] if self.stack else None
        hidden = self.stack[-1][2] if self.stack else False
        if not hidden:
            self.texts.append((lang, data))


IRISH = re.compile(r"\b(?:[A-Za-zÁÉÍÓÚáéíóú'’-]*[áéíóúÁÉÍÓÚ][A-Za-zÁÉÍÓÚáéíóú'’-]*"
                   r"|(?:[BDFGM]h|mB|gC|nD|bhF|nG|bP|dT)[a-záéíóú]{2,}"
                   r"|(?:n|t|h)-?[AEIOUÁÉÍÓÚ][a-záéíóú]{2,})\b")


def irish_hits(texts, allow):
    out = []
    for lang, t in texts:
        if lang and lang.startswith("ga"):
            continue
        for m in IRISH.finditer(t):
            w = m.group(0)
            if w in allow or w.lower() in allow:
                continue
            out.append(w)
    return out


def main():
    cfg_path = sys.argv[1]
    root = os.path.dirname(os.path.abspath(cfg_path))
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    base = os.path.normpath(os.path.join(root, cfg.get("root", ".")))
    R = []

    def rec(cid, name, status, detail=""):
        R.append({"id": cid, "check": name, "result": status, "detail": detail})
        print("%-4s %s %s%s" % (status, cid, name, (" :: " + json.dumps(detail, ensure_ascii=False)[:400]) if detail else ""))

    css = "".join(open(os.path.join(base, p), encoding="utf-8").read() for p in cfg["css"])
    themes = theme_tokens(css, cfg["themes"])
    exempt = cfg.get("contrast_exempt", {})
    for th, toks in themes.items():
        for tok, kind in cfg["text_tokens"].items():
            fg = toks.get(tok)
            if not fg or not HEX.fullmatch(fg):
                continue
            need = 3.0 if kind == "ui" else 4.5
            for bg_tok in cfg["surfaces"]:
                bg = toks.get(bg_tok)
                if not bg or not HEX.fullmatch(bg):
                    continue
                r = round(ratio(fg, bg), 2)
                key = "%s/%s" % (tok, bg_tok)
                ok = r >= need
                st = "PASS" if ok else ("WARN" if key in exempt or tok in exempt else "FAIL")
                rec("C1", "contrast %s --%s %s on --%s %s = %.2f:1 (need %.1f)" % (th, tok, fg, bg_tok, bg, r, need), st,
                    exempt.get(key) or exempt.get(tok) or "")
    motion = re.search(r"\b(transition|animation)\s*:", css)
    rm = "prefers-reduced-motion" in css
    rec("C3", "CSS motion has a prefers-reduced-motion override", "PASS" if (rm or not motion) else "FAIL")
    js_anim = []
    for p in cfg.get("js", []):
        s = open(os.path.join(base, p), encoding="utf-8").read()
        if re.search(r"flyTo\(|\.animate\(|requestAnimationFrame|behavior:\s*['\"]smooth", s) and "prefers-reduced-motion" not in s:
            js_anim.append(p)
    rec("C3", "JS animation consults prefers-reduced-motion", "PASS" if not js_anim else "WARN", js_anim)
    allow = set(cfg.get("irish_allow", []))
    maps = cfg.get("map_pages", {})
    for p in cfg["pages"]:
        pg = Page(); pg.feed(open(os.path.join(base, p), encoding="utf-8").read())
        rec("C4", "%s: <html lang=en>" % p, "PASS" if pg.html_lang == "en" else "FAIL", pg.html_lang)
        fl = pg.first_link or ""
        ok = fl.startswith("#") and fl[1:] in pg.ids
        rec("C2", "%s: skip link first and target exists" % p, "PASS" if ok else "FAIL", fl)
        ga = sum(1 for l, _ in pg.texts if l and l.startswith("ga"))
        hits = irish_hits(pg.texts, allow)
        rec("C5", "%s: Irish-looking text outside lang=ga (heuristic; %d lang=ga text runs)" % (p, ga),
            "PASS" if not hits else "WARN", sorted(set(hits))[:25])
        if p in maps:
            m = maps[p]
            rec("C6", "%s: non-map list view (%s)" % (p, m.get("list") or "none"), "PASS" if m.get("list") else "WARN", m.get("note", ""))
    if "--report" in sys.argv:
        json.dump(R, open(sys.argv[sys.argv.index("--report") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fails = [r for r in R if r["result"] == "FAIL"]
    print("a11y gate: %s (%d checks, %d FAIL, %d WARN)" % ("FAIL" if fails else "ok", len(R), len(fails),
                                                            sum(r["result"] == "WARN" for r in R)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
