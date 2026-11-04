REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 $REPO/official/vm/slow-server.py $PORT & SRV=$!
Q=$(pgrep -u $USER -f qemu-kvm | head -1); P=$(tr '\0' ' ' </proc/$Q/cmdline | grep -oE "hostfwd=tcp:127.0.0.1:[0-9]+" | grep -oE "[0-9]+$")
O=(-i /scratch/$USER/fm-vm/id -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
scp "${O[@]}" -P $P -q $REPO/official/fm_local/slow_probe.py fm@127.0.0.1:official/fm_local/slow_probe.py
scp "${O[@]}" -P $P -q $REPO/official/tests/guest-slow.sh fm@127.0.0.1:guest-slow.sh
ssh "${O[@]}" -p $P fm@127.0.0.1 "bash guest-slow.sh $PORT"
kill $SRV
