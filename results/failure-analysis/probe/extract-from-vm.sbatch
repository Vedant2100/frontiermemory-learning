#!/bin/bash
# READ-ONLY extraction of trial data from the VM disk. The disk is booted with snapshot=on, so every guest write
# goes to a throwaway overlay file; disk.qcow2, console.log and everything else under fm-vm are never written.
#SBATCH --job-name=fm-extract-ro
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=fm-extract-20261116/job-%j.log  # relative to the submit directory (home)
set -u
ROOT=/scratch/$USER/fm-vm; T=$HOME/fm-vm-tools/root; OUT=$HOME/fm-extract-20261116
export LD_LIBRARY_PATH=$T/usr/lib64:$T/usr/lib64/qemu-kvm
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
step "before: fingerprint of the originals"
stat -c '%n %s %Y' $ROOT/disk.qcow2 $ROOT/console.log $ROOT/frozen-20261103.qcow2 | tee $OUT/fingerprint-before.txt
SNAP=/scratch/$USER/fm-snap-$SLURM_JOB_ID; mkdir -p $SNAP; export TMPDIR=$SNAP
port() { python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])'; }
SP=$(port); SSH_PORT=$(port)
(cd $ROOT/seed && exec python3 -m http.server $SP --bind 127.0.0.1 >/dev/null 2>&1) & SEED_PID=$!
step "boot (snapshot=on, serial to scratch overlay dir)"
$T/usr/libexec/qemu-kvm -enable-kvm -cpu host -smp 4 -m 8192 -display none -vga none -serial file:$SNAP/console.log \
  -L $T/usr/share/seabios -L $T/usr/share/sgabios -L $T/usr/share/qemu-kvm \
  -drive file=$ROOT/disk.qcow2,if=virtio,snapshot=on \
  -smbios "type=1,serial=ds=nocloud-net;s=http://10.0.2.2:$SP/" \
  -netdev "user,id=n0,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22" -device virtio-net-pci,netdev=n0,romfile= & QEMU_PID=$!
O=(-i $ROOT/id -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR -o ServerAliveInterval=60)
G() { ssh "${O[@]}" -p $SSH_PORT fm@127.0.0.1 "$@"; }
cleanup() { G 'sudo poweroff' 2>/dev/null; sleep 20; kill $QEMU_PID $SEED_PID 2>/dev/null; step "after: fingerprint"; stat -c '%n %s %Y' $ROOT/disk.qcow2 $ROOT/console.log $ROOT/frozen-20261103.qcow2 | tee $OUT/fingerprint-after.txt; cmp $OUT/fingerprint-before.txt $OUT/fingerprint-after.txt && echo ORIGINALS_UNCHANGED; rm -rf $SNAP; }
trap cleanup EXIT
up=; for i in $(seq 1 90); do G true 2>/dev/null && { up=1; break; }; sleep 5; done
[ -n "$up" ] || { echo "guest SSH never came up"; tail -20 $SNAP/console.log; exit 1; }
step "guest up; inventory"
G 'df -h / | tail -1; ls ~/official/frontiermemory 2>&1 | head; sudo ls ~/official/frontiermemory/jobs 2>&1 | wc -l' | tee $OUT/inventory-basic.txt
G 'sudo du -sh ~/official/frontiermemory/jobs/* 2>/dev/null' > $OUT/inventory-jobs-size.txt; wc -l $OUT/inventory-jobs-size.txt
G 'sudo find ~/official/frontiermemory/jobs -type f -printf "%s %p\n"' > $OUT/inventory-all-files.txt; wc -l $OUT/inventory-all-files.txt
G 'sudo find / -xdev -type d \( -name hermes -o -name records \) -not -path "/proc/*" 2>/dev/null | head -50' > $OUT/inventory-hermes-dirs.txt
G 'sudo find / -xdev -type f \( -name MEMORY.md -o -name "*.skill.md" -o -name SKILL.md \) -not -path "/usr/*" -not -path "*/node_modules/*" -not -path "*/site-packages/*" -not -path "/proc/*" 2>/dev/null | head -2000' > $OUT/inventory-memory-files.txt; wc -l $OUT/inventory-memory-files.txt
step "choose size cap"
TOT=$(awk '$1<30*1048576{s+=$1} END{print s+0}' $OUT/inventory-all-files.txt); echo "bytes under 30MB cap: $TOT"
if [ "$TOT" -gt 60000000000 ]; then LIM=5242880; else LIM=31457280; fi; echo "cap bytes: $LIM"
awk -v l=$LIM '$1<l{ $1=""; sub(/^ /,""); print }' $OUT/inventory-all-files.txt > $OUT/list-jobs.txt
cat $OUT/inventory-memory-files.txt >> $OUT/list-jobs.txt
G 'sudo find /tmp/hermes -type f -size -30M 2>/dev/null' >> $OUT/list-jobs.txt
sort -u $OUT/list-jobs.txt -o $OUT/list-jobs.txt; wc -l $OUT/list-jobs.txt
step "stream tar to home"
G 'sudo tar -czf - --ignore-failed-read -T -' < $OUT/list-jobs.txt > $OUT/vm-trial-data.tar.gz 2> $OUT/tar.err
ls -la $OUT/vm-trial-data.tar.gz; tail -3 $OUT/tar.err
step "also fetch memory-related dirs listing for hermes"
G 'sudo ls -laR /tmp/hermes 2>/dev/null | head -400' > $OUT/inventory-tmp-hermes.txt
step done
