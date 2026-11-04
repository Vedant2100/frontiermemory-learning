cd ~/official/frontiermemory
sudo env PATH=$PWD/.venv/bin:$PATH PYTHONPATH=$HOME/official harbor run -p build/memory-task-v1.1 -a fm_local.slow_probe:SlowProbe -e docker --allow-agent-host 10.0.2.2 --ak "base=http://10.0.2.2:$1" --jobs-dir jobs --job-name slow-probe-test -y > /tmp/slow-run.log 2>&1
grep -vE '^[┏┡│└╭╰]|^$' /tmp/slow-run.log | grep -iE "error|exception|reward|trial" | tail -8 | cut -c1-160
sudo find jobs/slow-probe-test -name slow-probe.json -exec cat {} \;
sudo find jobs/slow-probe-test -name exception.txt -exec tail -5 {} \;
sudo rm -rf jobs/slow-probe-test
