#!/bin/bash
# Freeze the guest: turn off Docker's build-cache garbage collection, then keep a read-only copy of the disk.
# Harbor rebuilds images per trial, and most task builds have floating installs, so the build cache is what keeps every arm on the same dependencies. CPU only.
#SBATCH --job-name=fm-freeze
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=3
#SBATCH --mem=10G
#SBATCH --time=01:00:00
#SBATCH --output=official/logs/freeze-%j.log
source official/vm/lib.sh; vm_boot 2 6G || exit 1
G 'printf "{\"builder\":{\"gc\":{\"enabled\":false}}}\n" | sudo tee /etc/docker/daemon.json >/dev/null; sudo systemctl restart docker; sleep 3; sudo docker info --format "{{.ServerVersion}} {{.Driver}}"; cat /etc/docker/daemon.json; sudo docker system df | cut -c1-70; rm -f ~/.judge-key ~/key-audit-*.log; ls ~/.judge-key 2>/dev/null | wc -l' || exit 1
vm_stop; trap - EXIT; sleep 3
F=$ROOT/frozen-$(date +%Y%m%d).qcow2
cp --sparse=always "$ROOT/disk.qcow2" "$F" && chmod a-w "$F"; ls -la "$F" | cut -c1-90; du -sh "$F"; "$T/usr/bin/qemu-img" info "$F" | sed -n 1,4p; "$T/usr/bin/qemu-img" check "$F" 2>&1 | tail -2
sha256sum "$F" | cut -c1-16
echo FREEZE_DONE
