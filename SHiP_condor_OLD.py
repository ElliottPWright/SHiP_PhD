from __future__ import print_function

import argparse
import errno
import os
import shutil  # Import shutil to enable file copying
import subprocess
from distutils.spawn import find_executable


SHELL_SCRIPT = """
#!/usr/bin/env bash
set -e

echo "Running job $1"

PROCESS=$1
TAG=$2

source /cvmfs/sft.cern.ch/lcg/views/LCG_108/x86_64-el9-gcc13-opt/setup.sh

cd  GeoModelSplitCal/build

./run_g4

echo "Searching for output..."
FILE=$(ls calosim_out_*.root 2>/dev/null | head -n 1)

if [ -z "$FILE" ]; then
    echo "ERROR: no ROOT file found"
    ls -lh
    exit 1
fi

echo "Found: $FILE"
                                               
# CRITICAL: move into Condor root directory
cd "$_CONDOR_SCRATCH_DIR" 2>/dev/null || cd ../../

cp "GeoModelSplitCal/build/$FILE" "output_${PROCESS}.root"

xrdcp -f "output_${PROCESS}.root" \
root://eosuser.cern.ch//eos/home-e/elwright/EPWL_ECAL_Simulations/sim_runs/${TAG}/output/output_${PROCESS}.root


echo "Done"
"""



SUBMIT_FILE = """
universe = vanilla

Executable     = {shell_script_name}

log    = logs/calo_production.$(Cluster).$(Process).log
output = logs/calo_production.$(Cluster).$(Process).out
error  = logs/calo_production.$(Cluster).$(Process).err

request_cpus = 1
request_memory = 4GB
request_disk = 2GB

# Copy executable for safe recompiling
should_transfer_files = YES
when_to_transfer_output = ON_EXIT

transfer_output_files = output_$(Process).root

arguments = $(Process) {tag}
getenv = True

queue {njobs}
"""


def create_submit_script(output_dir, njobs, tag=""):

    out_dir = os.path.join(output_dir, tag)

    # Create necessary subdirectories for logs and output
    for subdir in ("logs", "output"):
        try:
            os.makedirs(os.path.join(out_dir, subdir))
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise type(e)(
                    "{} already exists, please delete or use a unique tag!".format(out_dir)
                )
            raise

    # Copy the macro file to the output directory for record-keeping

    shell_script_name = f".run_simulation_{abs(hash(out_dir))}.sh"

    return (
        SUBMIT_FILE.format(
            shell_script_name=shell_script_name,
            njobs=njobs, tag=tag
        ),
        shell_script_name,
    )


def submit():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("-n", type=int, required=True)
    parser.add_argument("--tag", "-t", default="")
    args = parser.parse_args()

    sub_file, script_name = create_submit_script(
        output_dir=args.output, njobs=args.n, tag=args.tag
    )

    with open("submit.sub", "w") as f:
        print(sub_file, file=f)
    with open(script_name, "w") as f:
        print(SHELL_SCRIPT, file=f)

    os.chmod(script_name, 0o755)

    # Now actually submit the jobs
    subprocess.call(["condor_submit", "submit.sub"])



if __name__ == "__main__":
    submit()
