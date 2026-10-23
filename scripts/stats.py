"""Genera assets/stats.svg y assets/langs.svg con la paleta Akaito.

Usa la API GraphQL de GitHub con el token de STATS_TOKEN (o GITHUB_TOKEN) para
incluir repos privados y de organizaciones en las estadísticas.
"""
import base64
import json
import os
import pathlib
import urllib.request
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = os.environ.get("STATS_USER", "SRibecca")
TOKEN = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")

W, H = 445, 200
BG, BAR_BG, BORDER = "#0d1117", "#161b22", "#a32f1a"
RED, ORANGE, CREAM, MUTED = "#e84d31", "#e48e3e", "#f3e4cb", "#9f8253"
PALETTE = ["#e84d31", "#e48e3e", "#d89b55", "#a8611f", "#a32f1a", "#9f8253"]
# Lenguajes que no son código escrito a mano
IGNORED = {"Makefile", "Batchfile", "CMake", "Shell", "PowerShell", "Dockerfile", "HLSL", "ShaderLab"}

# Íconos pixelarticons (24x24)
ICONS = {
    "git-commit": "<path fill=\"currentColor\" d=\"M9 7h6v2H9zM7 9h2v6H7zm2 6h6v2H9zm6-6h2v6h-2zM0 11h5v2H0zm19 0h5v2h-5z\"/>",
    "git-pull-request": "<path fill=\"currentColor\" d=\"M4 10h4V8H4zm0-6h4V2H4zM2 8h2V4H2zm6 0h2V4H8zm8 14h4v-2h-4zm0-6h4v-2h-4zm-2 4h2v-4h-2zm6 0h2v-4h-2zM12 7h5V5h-5zM5 22h2V12H5z\"/>",
    "eye": "<path fill=\"currentColor\" d=\"M16 20H8v-2h8zm-8-2H4v-2h4zm12 0h-4v-2h4zM4 16H2v-2h2zm10-6h-2v2h2zh2v4h-2v2h-4v-2H8v-4h2V8h4zm8 6h-2v-2h2zM2 14H0v-4h2zm22 0h-2v-4h2zM4 10H2V8h2zm18 0h-2V8h2zM8 8H4V6h4zm12 0h-4V6h4zm-4-2H8V4h8z\"/>",
    "folder": "<path fill=\"currentColor\" d=\"M4 4h6v2H4zm0 14h16v2H4zM20 8h2v10h-2zM2 6h2v12H2zm8 0h10v2H10z\"/>",
    "star": "<path fill=\"currentColor\" d=\"M5 20h3v2H3v-6h2zm16 2h-5v-2h3v-4h2zm-11-2H8v-2h2zm6 0h-2v-2h2zm-2-2h-4v-2h4zm-7-2H5v-3h2zm12 0h-2v-3h2zM5 13H3v-2h2zm16 0h-2v-2h2zM9 9H3v2H1V7h8zm14 2h-2V9h-6V7h8zM11 7H9V3h2zm4 0h-2V3h2zm-2-4h-2V1h2z\"/>",
}


def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL: {body['errors']}")
    return body["data"]


QUERY = """
query($login: String!) {
  user(login: $login) {
    pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestReviewContributions
    }
    repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], isFork: false) {
      nodes { ...repo }
    }
    repositoriesContributedTo(first: 100, includeUserRepositories: true,
                              contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {
      nodes { ...repo }
    }
  }
}
fragment repo on Repository {
  nameWithOwner
  isFork
  stargazerCount
  owner { login }
  languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
}
"""


def collect():
    user = graphql(QUERY, {"login": USER})["user"]
    repos = {}
    for r in user["repositories"]["nodes"] + user["repositoriesContributedTo"]["nodes"]:
        if not r["isFork"]:
            repos[r["nameWithOwner"]] = r
    langs = {}
    for r in repos.values():
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in IGNORED:
                langs[name] = langs.get(name, 0) + e["size"]
    cc = user["contributionsCollection"]
    stats = [
        ("git-commit", "Commits (último año)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("git-pull-request", "Pull requests", user["pullRequests"]["totalCount"]),
        ("eye", "Code reviews (último año)", cc["totalPullRequestReviewContributions"]),
        ("folder", "Repos con contribuciones", len(repos)),
        ("star", "Estrellas", sum(r["stargazerCount"] for r in repos.values() if r["owner"]["login"] == USER)),
    ]
    return stats, langs


def card(title, body):
    font = base64.b64encode((ROOT / "assets/fonts/pressstart.woff2").read_bytes()).decode()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
@font-face{{font-family:'PS2P';src:url(data:font/woff2;base64,{font}) format('woff2');}}
.title{{font-family:'PS2P',monospace;font-size:14px;fill:{RED};}}
text{{font-family:ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace;font-size:14px;fill:{CREAM};}}
.num{{fill:{ORANGE};font-weight:600;}}
.muted{{fill:{MUTED};}}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-opacity="0.6"/>
<text x="24" y="38" class="title">{escape(title)}</text>
{body}
</svg>
"""


def stats_svg(stats):
    rows = []
    for i, (icon, label, value) in enumerate(stats):
        y = 70 + i * 26
        rows.append(
            f'<g transform="translate(24 {y - 14}) scale(0.75)" color="{RED}">{ICONS[icon]}</g>'
            f'<text x="52" y="{y}">{escape(label)}</text>'
            f'<text x="{W - 24}" y="{y}" text-anchor="end" class="num">{value}</text>'
        )
    return card("Actividad", "\n".join(rows))


def langs_svg(langs):
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(size for _, size in top) or 1
    bar_w, x = W - 48, 24.0
    parts = [f'<clipPath id="bar"><rect x="24" y="58" width="{bar_w}" height="10" rx="5"/></clipPath>',
             f'<g clip-path="url(#bar)"><rect x="24" y="58" width="{bar_w}" height="10" fill="{BAR_BG}"/>']
    for (_, size), color in zip(top, PALETTE):
        w = bar_w * size / total
        parts.append(f'<rect x="{x:.2f}" y="58" width="{w + 0.5:.2f}" height="10" fill="{color}"/>')
        x += w
    parts.append("</g>")
    for i, ((name, size), color) in enumerate(zip(top, PALETTE)):
        cx, cy = 24 + (i % 2) * 205, 100 + (i // 2) * 30
        parts.append(
            f'<rect x="{cx}" y="{cy - 10}" width="10" height="10" fill="{color}"/>'
            f'<text x="{cx + 18}" y="{cy}">{escape(name)}</text>'
            f'<text x="{cx + 185}" y="{cy}" text-anchor="end" class="muted">{100 * size / total:.1f}%</text>'
        )
    return card("Lenguajes", "\n".join(parts))


def main():
    if not TOKEN:
        raise SystemExit("Falta STATS_TOKEN: agregalo en Settings > Secrets and variables > Actions")
    stats, langs = collect()
    (ROOT / "assets/stats.svg").write_text(stats_svg(stats))
    (ROOT / "assets/langs.svg").write_text(langs_svg(langs))
    print("stats:", stats)
    print("langs:", sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6])


if __name__ == "__main__":
    main()
