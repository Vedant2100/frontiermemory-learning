# Boot the existing Docker guest (built by build-and-test-vm.sbatch) and give a job ${SSH[@]} and SCP.
# Usage: source official/vm/lib.sh; vm_boot <cpus> <mem>
ROOT=/scratch/$USER/fm-vm
T=$HOME/fm-vm-tools/root
export LD_LIBRARY_PATH=$T/usr/lib64:$T/usr/lib64/qemu-kvm
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
  "${SSH[@]}" 'sudo poweroff' 2>/dev/null || true
  for _ in $(seq 1 12); do kill -0 "$QEMU_PID" 2>/dev/null || break; sleep 5; done
  kill "$QEMU_PID" "$SEED_PID" 2>/dev/null || true
}
