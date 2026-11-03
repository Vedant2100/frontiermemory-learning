#!/bin/bash
# Build a KVM guest with official Docker Engine on local scratch and prove Docker works (D68). CPU only.
#SBATCH --job-name=fm-vm-build
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=official/logs/vm-build-%j.log
set -euo pipefail
ROOT=/scratch/$USER/fm-vm; mkdir -p "$ROOT"; cd "$ROOT"; chmod 700 "$ROOT"
export CONDA_PKGS_DIRS=$ROOT/pkgs
step() { echo "=== $(date +%H:%M:%S) $*"; }

step "kvm"; ls -l /dev/kvm
step "qemu"
# Rocky's signed QEMU packages, unpacked (not installed) in $HOME/fm-vm-tools. Signatures checked with rpm -K.
T=$HOME/fm-vm-tools/root
export LD_LIBRARY_PATH=$T/usr/lib64:$T/usr/lib64/qemu-kvm
QEMU=$T/usr/libexec/qemu-kvm; QIMG=$T/usr/bin/qemu-img
"$QEMU" --version | head -1

step "image"
[ -f base.img ] || curl -fsSL -o base.img https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
[ -f id ] || ssh-keygen -q -t ed25519 -N '' -f id
rm -f disk.qcow2; "$QIMG" create -q -f qcow2 -b base.img -F qcow2 disk.qcow2 400G

mkdir -p seed
cat > seed/meta-data <<META
instance-id: fm-vm-$(date +%s)
local-hostname: fm-vm
META
cat > seed/user-data <<USER
#cloud-config
users:
  - name: fm
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys: ["$(cat id.pub)"]
USER
SEED_PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
SSH_PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
(cd seed && exec python3 -m http.server "$SEED_PORT" --bind 127.0.0.1 >/dev/null 2>&1) & SEED_PID=$!

step "boot"
"$QEMU" -enable-kvm -cpu host -smp 6 -m 12G -display none -vga none -serial "file:$ROOT/console.log" \
  -L "$T/usr/share/seabios" -L "$T/usr/share/sgabios" -L "$T/usr/share/qemu-kvm" \
  -drive file=disk.qcow2,if=virtio \
  -smbios "type=1,serial=ds=nocloud-net;s=http://10.0.2.2:$SEED_PORT/" \
  -netdev "user,id=n0,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22" -device virtio-net-pci,netdev=n0,romfile= & QEMU_PID=$!
trap 'kill $SEED_PID 2>/dev/null || true; kill $QEMU_PID 2>/dev/null || true' EXIT
SSH=(ssh -i id -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR fm@127.0.0.1)
for i in $(seq 1 60); do "${SSH[@]}" true 2>/dev/null && break; sleep 5; [ "$i" = 60 ] && { echo "SSH never came up"; tail -20 console.log; exit 1; }; done
echo "ssh up after about $((i*5)) s"

step "docker install (official repo)"
"${SSH[@]}" 'cloud-init status --wait >/dev/null; sudo install -m 0755 -d /etc/apt/keyrings && sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && sudo chmod a+r /etc/apt/keyrings/docker.asc && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null && sudo apt-get -qq update && sudo apt-get -qq -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin >/tmp/docker-install.log 2>&1 || { tail -20 /tmp/docker-install.log; exit 1; }; sudo usermod -aG docker fm'

step "tests"
"${SSH[@]}" 'uname -r; . /etc/os-release; echo "$PRETTY_NAME"; docker --version; docker compose version; df -h / | tail -1; nproc; free -g | sed -n 2p
sudo docker run --rm hello-world | sed -n 2p
echo "host via 10.0.2.2: $(curl -s -o /dev/null -m 8 -w "%{http_code}" http://10.0.2.2:'"$SEED_PORT"'/meta-data)"
for u in https://public.ecr.aws/v2/ https://github.com https://huggingface.co; do echo "$u $(curl -s -o /dev/null -m 10 -w "%{http_code}" $u)"; done
sudo docker run --rm --network none alpine sh -c "wget -q -T 5 -O- http://example.com >/dev/null 2>&1 && echo no-network-LEAK || echo no-network-blocks-OK"'
step "shutdown"
"${SSH[@]}" 'sudo poweroff' || true; sleep 10
echo "VM_BUILD_OK"
