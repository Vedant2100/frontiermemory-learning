#!/bin/bash
# Read-only: which tools can open the VM disk image without root, and does the image look intact.
#SBATCH --job-name=fm-probe-tools
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=results/failure-analysis/probe/probe-tools-%j.log
D=/scratch/$USER/fm-vm
hostname; date; id -un >/dev/null
for t in qemu-img qemu-nbd qemu-system-x86_64 guestfish virt-ls virt-copy-out libguestfs-test-tool guestmount; do printf "%s: " $t; command -v $t || echo none; done
ls ~/fm-vm-tools 2>&1 | head -20
echo "--- image info (read-only, force-share)"
qemu-img info -U $D/disk.qcow2 2>&1 | head -15
echo "--- nbd/fuse/userns"
ls /dev/nbd0 /dev/fuse 2>&1 | head; cat /proc/sys/user/max_user_namespaces 2>&1
echo "--- running qemu now?"; pgrep -af qemu | head -3
