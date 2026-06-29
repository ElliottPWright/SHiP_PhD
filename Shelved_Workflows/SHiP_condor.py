from __future__ import print_function

import argparse
import os
import subprocess


# -----------------------------
# Shell script executed on node
# -----------------------------
SHELL_SCRIPT = """
#!/usr/bin/env bash
set -e

PROCESS=$1
TAG=$2

source /cvmfs/sft.cern.ch/lcg/views/LCG_108/x86_64-el9-gcc13-opt/setup.sh

xrdcp -f root://eosuser.cern.ch//eos/user/e/elwright/GeoModelSplitCal/build/run_g4 .
chmod +x run_g4

./run_g4

test -f  "*.root"

"""


# -----------------------------
# Submit file (NO EOS paths here except output storage)
# -----------------------------
SUBMIT_FILE = """universe = vanilla

Executable = .run_simulation_{script_id}.sh

log    = {out_dir}/logs/job.$(Cluster).$(Process).log
output = {out_dir}/logs/job.$(Cluster).$(Process).test
error  = {out_dir}/logs/job.$(Cluster).$(Process).test

request_cpus = 1
request_memory = 4GB
request_disk = 2GB

should_transfer_files = YES
when_to_transfer_output = ON_EXIT

transfer_output_files = output.root
transfer_output_remaps = "output.root = {out_dir}/output/output_$(Process).root"

arguments = $(Process)

queue {njobs}
"""


# -----------------------------
# Build submit + script
# -----------------------------


def create_submit_script(output_dir, njobs, tag=""):

    os.makedirs("logs", exist_ok=True)
    out_dir = os.path.join(output_dir, tag)
    script_name = f".run_simulation_{abs(hash(output_dir))}.sh"

    submit_text = SUBMIT_FILE.format(
        script_id=abs(hash(output_dir)),
        out_dir=os.path.abspath(out_dir),
        njobs=njobs,
    )

    return submit_text, script_name


# -----------------------------
# Main submit function
# -----------------------------
def submit():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-n", type=int, required=True)
    parser.add_argument("-t", "--tag", default="run")

    args = parser.parse_args()

    # MUST run from AFS, not EOS
    if os.getcwd().startswith("/eos"):
        raise RuntimeError("Do NOT submit from EOS. Run from AFS or home directory.")

    sub_file, script_name = create_submit_script(
        njobs=args.n,
        tag=args.tag,
        output_dir=args.output
    )

    with open("submit.sub", "w") as f:
        f.write(sub_file)

    with open(script_name, "w") as f:
        f.write(SHELL_SCRIPT)

    os.chmod(script_name, 0o755)

    print("Submitting jobs...")
    subprocess.call(["condor_submit", "submit.sub"])
    print("Done")


if __name__ == "__main__":
    submit()
                       
