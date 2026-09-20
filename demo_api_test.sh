#!/usr/bin/env bash
# Quick API sanity check for the demo recording.
# Hits /api/v1/analyze/text with two English legal queries and confirms
# a real grounded answer + citations + playable audio comes back.
set -euo pipefail

API="http://localhost:8000/api/v1/analyze/text"
OUT_DIR="/tmp/legalfriend_demo"
mkdir -p "$OUT_DIR"

run_query() {
  local name="$1"
  local query="$2"
  echo "=== $name ==="
  local out="$OUT_DIR/${name}.json"
  local start end
  start=$(date +%s)
  curl -s -X POST "$API" \
    -H "Content-Type: application/json" \
    -H "x-session-id: demo-${name}" \
    -d "{\"query\": \"${query}\", \"source_lang_code\": \"en-IN\", \"target_lang_code\": \"en-IN\"}" \
    -o "$out" -w "HTTP %{http_code}\n" --max-time 90
  end=$(date +%s)
  echo "took $((end - start))s"
  python3 - "$out" "$OUT_DIR/${name}.wav" <<'PY'
import json, base64, sys
out_path, wav_path = sys.argv[1], sys.argv[2]
d = json.load(open(out_path))
print("transcript:", d.get("advice", {}).get("transcript", "")[:300], "...")
print("citations:", len(d.get("citations", [])))
b64 = d.get("advice", {}).get("audio_payload_b64")
if b64:
    audio = base64.b64decode(b64)
    open(wav_path, "wb").write(audio)
    print(f"audio: {len(audio)} bytes -> {wav_path}")
else:
    print("audio: MISSING")
PY
  echo
}

run_query "jail-threat" "A recovery agent called me at midnight and said I would be sent to jail if I do not pay interest at 1% per day on my loan. Is this legal? What should I do?"

run_query "cheque-bounce" "My cheque bounced and the lender is threatening to file a criminal case against me and send police to my house. What are my rights?"

echo "Done. Play the audio to verify: afplay $OUT_DIR/jail-threat.wav"
