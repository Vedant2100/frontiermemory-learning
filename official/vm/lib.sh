# Boot the existing Docker guest (built by build-and-test-vm.sbatch) and give a job ${SSH[@]} and SCP.
# Usage: source official/vm/lib.sh; vm_boot <cpus> <mem>
ROOT=/scratch/$USER/fm-vm
T=$HOME/fm-vm-tools/root
export LD_LIBRARY_PATH=$T/usr/lib64:$T/usr/lib64/qemu-kvm
PROBE_IMAGE=alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11  # Harbor's kernel probe: an uncached slow pull reads as "no-network unsupported"
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
G() { "${SSH[@]}" "$@"; }
free_port() { python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])'; }

vm_boot() {
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
  for i in $(seq 1 60); do "${SSH[@]}" true 2>/dev/null && return 0; sleep 5; done
  echo "guest SSH never came up"; tail -20 "$ROOT/console.log"; return 1
}

vm_stop() {
  "${SSH[@]}" 'rm -f ~/.judge-key; sudo poweroff' 2>/dev/null || true
  for _ in $(seq 1 12); do kill -0 "$QEMU_PID" 2>/dev/null || break; sleep 5; done
  kill "$QEMU_PID" "$SEED_PID" ${RELAY_PID:+"$RELAY_PID"} 2>/dev/null || true
}

# Serve the model on the host GPUs, at the model's full context, behind the relay (fm_local/model_relay.py), which
# answers before Harbor's egress proxy cuts a response with no first byte at 15 s (D93).
# Sets PORT (Ollama), RELAY_PORT (what the guest uses), OLLAMA_PID, RELAY_PID, OLOG.
model_up() {
  local repo=$1; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
  apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
    --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
    --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env TMPDIR=/ollama-logs/tmp \
    "$repo/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
  local up=; for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && { up=1; break; }; sleep 2; done
  [ -n "$up" ] || { echo "MODEL_SERVER_FAILED"; return 1; }
  RELAY_PORT=$(free_port)
  python3 "$repo/official/fm_local/model_relay.py" "$RELAY_PORT" "$PORT" "$OLOG/relay.log" >>"$OLOG/relay.err" 2>&1 & RELAY_PID=$!
  for _ in $(seq 1 15); do curl -fs -m 3 "http://127.0.0.1:$RELAY_PORT/api/version" >/dev/null && return 0; sleep 1; done
  echo "MODEL_RELAY_FAILED"; return 1
}
