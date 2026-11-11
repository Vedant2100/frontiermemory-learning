#!/bin/bash
# Build an anonymous "plan archive" for a public timestamp (OSF, Zenodo or similar): the written plans, a list of when each plan
# version was tagged, and the SHA-256 of the plan file at every tag, so a later reader can check that nothing was changed after
# the deposit. Contains no names, commit hashes or paths. It attests what the files said on the deposit date; the earlier tag dates
# are the authors' own version-control records, and the archive does not prove that the plan predates the results.
# Usage: scripts/build_deposit.sh OUT_DIR   (writes OUT_DIR/fm-plan-archive.zip; uploads nothing)
set -euo pipefail
OUT=${1:?output directory}; REPO=$(cd "$(dirname "$0")/.." && pwd); cd "$REPO"
S=$(mktemp -d); A=$S/fm-plan-archive; mkdir -p "$A"
for f in results/preregistration-v2.md results/preregistration-arms.md results/protocol-v4-official.md; do cp "$f" "$A/$(basename "$f")"; done
sed -i -E -e 's#/home/csgrad/vbork001[^ )`"]*#/path/to/repo#g' -e 's/nodevcggpu[0-9]*/gpu-node/g' -e 's/vbork001|csgrad|Vedant[A-Za-z0-9-]*|compfly/anon/g' -e 's/[Bb]ender/second-machine/g' "$A"/*.md
{
  echo "tag<TAB>tagged (local time)<TAB>plan file<TAB>sha256 of that file at the tag"
  for t in $(git tag --list 'prereg-v2*' 'prereg-arms*' --sort=creatordate); do
    case "$t" in prereg-arms*) f=results/preregistration-arms.md;; *) f=results/preregistration-v2.md;; esac
    printf '%s\t%s\t%s\t%s\n' "$t" "$(git log -1 --format=%ci "$t")" "$(basename "$f")" "$(git show "$t:$f" | sha256sum | cut -d' ' -f1)"
  done
} | sed 's/<TAB>/\t/g' > "$A/plan-tags.tsv"
cat > "$A/README.md" <<'R'
# Plan archive: FrontierMemory audit

This archive holds the written plans of one study (an audit of a memory benchmark for coding agents) and a record of when each
version was tagged in the authors' version control.

- `preregistration-v2.md`: the main plan (design, primary test, checks) and its dated amendments A1 to A7.
- `preregistration-arms.md`: the plan for the exploratory arms and its dated amendments B1 to B6.
- `protocol-v4-official.md`: the run protocol, item by item, with every difference from the official pipeline.
- `plan-tags.tsv`: for each tag, the local time it was created and the SHA-256 of the plan file as it stood at that tag.
- `SHA256SUMS`: SHA-256 of every file in this archive (`sha256sum -c SHA256SUMS`).

What this attests: the content of these files on the deposit date, and, with `plan-tags.tsv`, which earlier versions the authors
recorded. What it does not attest: that those earlier versions were recorded before any result existed. That rests on the authors'
own version-control timestamps, which no third party witnessed. The plans were not filed with a public registry before the study.
R
(cd "$A" && sha256sum * > SHA256SUMS)
if grep -rniE 'vbork001|csgrad|vedant|compfly|nodevcggpu|bender|/home/' "$A"; then echo "DEPOSIT_LEAK: identifiers remain; nothing written"; rm -r "$S"; exit 1; fi
mkdir -p "$OUT"; rm -f "$OUT/fm-plan-archive.zip"; (cd "$S" && zip -qr "$OUT/fm-plan-archive.zip" fm-plan-archive)
echo "files: $(ls "$A" | wc -l)  size: $(du -sh "$OUT/fm-plan-archive.zip" | cut -f1)"; rm -r "$S"; echo "DEPOSIT_OK $OUT/fm-plan-archive.zip"
