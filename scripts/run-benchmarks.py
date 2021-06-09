#!/usr/bin/env python3

import argparse
from pathlib import Path
import subprocess

PROJECTS = {'baseline':'freertos_microbenchmarks_clang', 
                   'baseline_mpu':'freertos_mpu_microbenchmarks_clang',
                   'kage':'microbenchmarks'}
DEVICE = 'demos/st/stm32l475_discovery/ac6'
OCD_CMD = 'program $PATH$ reset exit'

# Main routine
if __name__ == "__main__":
    # Argparse
    parser = argparse.ArgumentParser()
    # Optional custom workspace path
    parser.add_argument('--workspace', type=Path, default=Path('../workspace'))
    # Optional custom OpenOCD binary path
    parser.add_argument('--openocd', type=str, default='openocd')
    # Optional OpenOCD configuration path
    parser.add_argument('--ocdcfg', type=Path, \
        default='/usr/share/openocd/scripts/board/st_b-l475e-iot01a.cfg')
    # Optional subset of projects
    parser.add_argument('--projects', type=str, nargs='+', \
        default=['baseline', 'baseline_mpu', 'kage'])
    # Get arguments
    args = parser.parse_args()

    # Generate project paths
    for project in args.projects:
        if not project in PROJECTS:
            print('ERROR: Unknown project ', project)
            exit()
        projectPath = Path(args.workspace).joinpath(PROJECTS[project]).joinpath(DEVICE)
        print('Running ', project)
        for configDir in projectPath.iterdir():
            if not configDir.is_dir():
                continue
            if configDir.name[0] == '.':
                continue
            # Execute OpenOCD on binary found in each build config
            binPath = configDir.joinpath(configDir.name + '.elf')
            ocdArg = OCD_CMD.replace('$PATH$', binPath.as_posix())
            subprocess.run([args.openocd, '-f', args.ocdcfg.as_posix(), '-c', \
                ocdArg])
            print('Finished ', binPath.name)
            # Pause until user input
            input('Press Enter to continue')