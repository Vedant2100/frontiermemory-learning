# Boot the existing Docker guest (built by build-and-test-vm.sbatch) and give a job ${SSH[@]} and SCP.
# Usage: source official/vm/lib-cluster2.sh; vm_boot <cpus> <mem>
ROOT=/tmp/fm-c2-$USER
T=
PROBE_IMAGE=alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11  # Harbor's kernel probe: an uncached slow pull reads as "no-network unsupported"
# Harbor may request the tag form; keep it aliased to this pinned digest.
PROBE_IMAGE_TAG=${PROBE_IMAGE%%@*}
GUEST_DNS_SERVER=169.235.16.10  # UCR primary resolver; the QEMU DNS proxy intermittently times out on Docker auth lookups.
mkdir -p "$ROOT"
chmod 700 "$ROOT"
SSH=(); SCP=(); QEMU_PID=; SEED_PID=; C2_VM_LOCKED=0
OLLAMA_PID=; OLLAMA_PGID=; RELAY_PID=
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
G() { "${SSH[@]}" "set -euo pipefail; $*"; }
free_port() { python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])'; }

stop_pid() {
  local pid=${1:-}
  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 5); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  kill -KILL "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

stop_model_server() {
  local pid=${OLLAMA_PID:-} pgid=${OLLAMA_PGID:-}
  if [[ "$pgid" =~ ^[0-9]+$ ]] && (( pgid > 1 )); then
    # model_up starts Apptainer in its own session so the Ollama process and its
    # fakeroot helpers share a private process group. Killing only Apptainer
    # leaves the GPU-owning Ollama child alive on this host.
    kill -TERM -- "-$pgid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 -- "-$pgid" 2>/dev/null || break
      sleep 1
    done
    kill -KILL -- "-$pgid" 2>/dev/null || true
    [[ "$pid" =~ ^[0-9]+$ ]] && wait "$pid" 2>/dev/null || true
  else
    stop_pid "$pid"
  fi
  OLLAMA_PID=; OLLAMA_PGID=
}

stop_relay() {
  stop_pid "${RELAY_PID:-}"
  RELAY_PID=
}

acquire_study_lock() {
  if [ "${C2_LOCK_HELD:-0}" = 1 ]; then
    local locked_path
    locked_path=$(readlink -f "/proc/$$/fd/9" 2>/dev/null || true)
    [ "$locked_path" = "$ROOT/study.lock" ] || { echo STUDY_LOCK_NOT_INHERITED >&2; return 1; }
    return 0
  fi
  exec 9>"$ROOT/study.lock"
  flock -n 9 || { echo STUDY_LOCK_BUSY >&2; exec 9>&-; return 1; }
  C2_LOCK_HELD=1
  export C2_LOCK_HELD
}

vm_boot() {
  if [ "$C2_VM_LOCKED" != 1 ]; then
    exec 8>"$ROOT/vm.lock"
    flock -n 8 || { echo OWN_VM_BUSY >&2; exec 8>&-; return 1; }
    C2_VM_LOCKED=1
  fi
  local cpus=$1 mem=$2 seed_port; seed_port=$(free_port); SSH_PORT=$(free_port)
  (cd "$ROOT/seed" && exec python3 -m http.server "$seed_port" --bind 127.0.0.1 >/dev/null 2>&1) & SEED_PID=$!
  "$T/usr/libexec/qemu-kvm" -enable-kvm -cpu host -smp "$cpus" -m "$mem" -display none -vga none -serial "file:$ROOT/console.log" \
    -L "$T/usr/share/seabios" -L "$T/usr/share/sgabios" -L "$T/usr/share/qemu-kvm" \
    -drive "file=$ROOT/disk.qcow2,if=virtio" \
    -smbios "type=1,serial=ds=nocloud-net;s=http://10.0.2.2:$seed_port/" \
    -netdev "user,id=n0,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22" -device virtio-net-pci,netdev=n0,romfile= & QEMU_PID=$!
  trap 'vm_stop' EXIT
  local o=(-i "$ROOT/id" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR -o ServerAliveInterval=60)
  SSH=(ssh "${o[@]}" -p "$SSH_PORT" fm@127.0.0.1); SCP=(scp "${o[@]}" -P "$SSH_PORT" -q -r)
  for i in $(seq 1 60); do
    if "${SSH[@]}" true 2>/dev/null; then
      configure_guest_dns || return 1
      return 0
    fi
    sleep 5
  done
  echo "guest SSH never came up"; tail -20 "$ROOT/console.log"; return 1
}

configure_guest_dns() {
  "${SSH[@]}" "sudo bash -s -- '$GUEST_DNS_SERVER'" <<'REMOTE'
set -euo pipefail
dns=$1
iface=$(ip -4 route show default | awk 'NR == 1 {print $5}')
[[ "$iface" =~ ^[[:alnum:]_.-]+$ ]] || { echo GUEST_DNS_INTERFACE_NOT_FOUND >&2; exit 1; }
network_file=$(networkctl status "$iface" --no-pager | sed -n 's/^[[:space:]]*Network File: //p')
expected="/run/systemd/network/10-netplan-${iface}.network"
[[ "$network_file" == "$expected" ]] || { echo "UNEXPECTED_GUEST_NETWORK_FILE=$network_file" >&2; exit 1; }
dropin_dir="/etc/systemd/network/$(basename "$network_file").d"
install -d -m 0755 "$dropin_dir"
dropin="$dropin_dir/50-cluster2-dns.conf"
tmp="$dropin.tmp.$$"
printf '[Network]\nDNS=%s\n\n[DHCPv4]\nUseDNS=no\n\n[DHCPv6]\nUseDNS=no\n\n[IPv6AcceptRA]\nUseDNS=no\n' "$dns" > "$tmp"
chmod 0644 "$tmp"
if ! cmp -s "$dropin" "$tmp" 2>/dev/null; then
  mv "$tmp" "$dropin"
  networkctl reload
else
  rm -f "$tmp"
fi
resolvectl flush-caches
actual=
for attempt in $(seq 1 20); do
  actual=$(resolvectl dns "$iface" | sed -E 's/^Link [0-9]+ \([^)]*\): //')
  [[ "$actual" == "$dns" ]] && break
  sleep 1
done
[[ "$actual" == "$dns" ]] || { echo "GUEST_DNS_MISMATCH actual=$actual expected=$dns" >&2; exit 1; }
all_dns=$(resolvectl dns | awk -F': ' 'NF > 1 {n = split($NF, servers, " "); for (i = 1; i <= n; i++) if (servers[i] != "") print servers[i]}' | sort -u | tr '\n' ' ' | sed 's/ $//')
[[ "$all_dns" == "$dns" ]] || { echo "GUEST_DNS_SET_MISMATCH actual=$all_dns expected=$dns" >&2; exit 1; }
printf 'GUEST_DNS_CONFIGURED link=%s server=%s persistent_dropin=%s\n' "$iface" "$dns" "$dropin"
REMOTE
}

vm_stop() {
  if ((${#SSH[@]})); then "${SSH[@]}" 'rm -f ~/.judge-key; sudo poweroff' 2>/dev/null || true; fi
  for _ in $(seq 1 12); do [ -n "$QEMU_PID" ] && kill -0 "$QEMU_PID" 2>/dev/null || break; sleep 5; done
  for pid in "$QEMU_PID" "$SEED_PID"; do
    [[ "$pid" =~ ^[0-9]+$ ]] && kill "$pid" 2>/dev/null || true
  done
  [ -n "$QEMU_PID" ] && wait "$QEMU_PID" 2>/dev/null || true
  [ -n "$SEED_PID" ] && wait "$SEED_PID" 2>/dev/null || true
  stop_relay
  stop_model_server
  SSH=(); SCP=(); QEMU_PID=; SEED_PID=
  if [ "$C2_VM_LOCKED" = 1 ]; then C2_VM_LOCKED=0; exec 8>&-; fi
}

# Serve the model on the host GPUs, at the model's full context, behind the relay (fm_local/model_relay.py), which
# answers before Harbor's egress proxy cuts a response with no first byte at 15 s (D93).
# Sets PORT (Ollama), RELAY_PORT (what the guest uses), OLLAMA_PID, RELAY_PID, OLOG.
model_up() {
  local repo=$1; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
  setsid apptainer exec --fakeroot --nv --home "$ROOT/ollama-home" --bind /tmp/fm-c2-$USER/models:/models:ro --bind "$OLOG:/ollama-logs" \
    --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
    --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env TMPDIR=/ollama-logs/tmp \
    "$ROOT/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
  local shell_pgid pgid
  shell_pgid=$(ps -o pgid= -p "$$" | tr -d ' ')
  for _ in $(seq 1 50); do
    pgid=$(ps -o pgid= -p "$OLLAMA_PID" 2>/dev/null | tr -d ' ' || true)
    if [[ "$pgid" =~ ^[0-9]+$ && "$pgid" != "$shell_pgid" ]]; then OLLAMA_PGID=$pgid; break; fi
    kill -0 "$OLLAMA_PID" 2>/dev/null || break
    sleep 0.1
  done
  [[ "$OLLAMA_PGID" =~ ^[0-9]+$ ]] || { echo MODEL_SERVER_PROCESS_GROUP_FAILED; return 1; }
  local up=; for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && { up=1; break; }; sleep 2; done
  [ -n "$up" ] || { echo "MODEL_SERVER_FAILED"; return 1; }
  RELAY_PORT=$(free_port)
  python3 "$repo/official/fm_local/model_relay.py" "$RELAY_PORT" "$PORT" "$OLOG/relay.log" >>"$OLOG/relay.err" 2>&1 & RELAY_PID=$!
  for _ in $(seq 1 15); do curl -fs -m 3 "http://127.0.0.1:$RELAY_PORT/api/version" >/dev/null && return 0; sleep 1; done
  echo "MODEL_RELAY_FAILED"; return 1
}
