#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
#  SMS-API Qualification Test
#  Usage:  ./scripts/qualification_test.sh <API_BASE_URL>
#  Example: ./scripts/qualification_test.sh http://localhost:8080
#           ./scripts/qualification_test.sh https://your-alb.example.com
# ──────────────────────────────────────────────────────────────────
set -uo pipefail

API_BASE_URL="${1:?Usage: $0 <API_BASE_URL>}"
REPO="https://github.com/CovertLabEcoli/vEcoli-private"
BRANCH="master"

# Helper: strip ANSI escape codes from Rich CLI output
strip_ansi() { sed 's/\x1b\[[0-9;]*m//g'; }

# Helper: print error and exit
die() { echo ""; echo "  ✗ ERROR: $*" >&2; echo ""; exit 1; }

# Helper: extract first integer from captured output matching a grep pattern.
# Prints the error output and exits if nothing is found.
extract_id() {
  local label="$1"
  local captured="$2"
  local pattern="$3"
  local id
  id=$(echo "$captured" | strip_ansi | grep -iE "$pattern" | grep -oE '[0-9]+' | head -1 || true)
  if [[ -z "$id" ]]; then
    echo ""
    echo "── command output ───────────────────────────────────────────"
    echo "$captured"
    echo "─────────────────────────────────────────────────────────────"
    die "${label}: ID not found in output above (searched for '${pattern}')"
  fi
  echo "$id"
}

# ── Step 1: Build / resolve simulator ──────────────────────────────
echo "▸ Step 1/5 — Build simulator from ${REPO} (${BRANCH})"
if ! SIM_OUT=$(uv run atlantis simulator latest \
    --repo-url "$REPO" \
    --branch "$BRANCH" \
    --base-url "$API_BASE_URL" 2>&1); then
  echo "── command output ───────────────────────────────────────────"
  echo "$SIM_OUT"
  echo "─────────────────────────────────────────────────────────────"
  die "simulator latest failed"
fi
SIM_ID=$(extract_id "simulator latest" "$SIM_OUT" "simulator id")
echo "  ✓ Simulator ready — ID: ${SIM_ID}"

# ── Step 2: Short simulation (1 gen, 1 seed) ───────────────────────
echo "▸ Step 2/5 — Short simulation (1 generation, 1 seed)"
if ! SHORT_OUT=$(uv run atlantis simulation run qual_short "$SIM_ID" \
    --generations 1 \
    --seeds 1 \
    --run-parca \
    --poll \
    --base-url "$API_BASE_URL" 2>&1); then
  echo "── command output ───────────────────────────────────────────"
  echo "$SHORT_OUT"
  echo "─────────────────────────────────────────────────────────────"
  die "simulation run (short) failed"
fi
SHORT_ID=$(extract_id "simulation run (short)" "$SHORT_OUT" "simulation (submitted|id)")
echo "  ✓ Short simulation complete — ID: ${SHORT_ID}"

# ── Step 3: Export short results ───────────────────────────────────
echo "▸ Step 3/5 — Export short simulation results"
uv run atlantis simulation outputs "$SHORT_ID" \
  --dest ./qual_short_outputs \
  --base-url "$API_BASE_URL" \
  || die "simulation outputs (short) failed"
echo "  ✓ Results → ./qual_short_outputs"

# ── Step 4: Large simulation (4 gen, 4 seeds) ──────────────────────
# Note: parca dataset from step 2 is reused automatically — --run-parca
# is not passed here to avoid an unnecessary second parca run.
echo "▸ Step 4/5 — Large simulation (4 generations, 4 seeds)"
if ! LARGE_OUT=$(uv run atlantis simulation run qual_large "$SIM_ID" \
    --generations 4 \
    --seeds 4 \
    --poll \
    --base-url "$API_BASE_URL" 2>&1); then
  echo "── command output ───────────────────────────────────────────"
  echo "$LARGE_OUT"
  echo "─────────────────────────────────────────────────────────────"
  die "simulation run (large) failed"
fi
LARGE_ID=$(extract_id "simulation run (large)" "$LARGE_OUT" "simulation (submitted|id)")
echo "  ✓ Large simulation complete — ID: ${LARGE_ID}"

# ── Step 5: Export large results ───────────────────────────────────
echo "▸ Step 5/5 — Export and verify large simulation results"
uv run atlantis simulation outputs "$LARGE_ID" \
  --dest ./qual_large_outputs \
  --base-url "$API_BASE_URL" \
  || die "simulation outputs (large) failed"
FILE_COUNT=$(find ./qual_large_outputs -type f | wc -l | tr -d ' ')
echo "  ✓ Results → ./qual_large_outputs (${FILE_COUNT} files)"

cat <<'EOF'

══════════════════════════════════════════════════════════
  ✓  Qualification test PASSED
══════════════════════════════════════════════════════════
EOF
