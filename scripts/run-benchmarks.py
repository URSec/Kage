#!/usr/bin/env python3

import argparse
from pathlib import Path
import subprocess
from sys import stderr

PROJECTS = {'microbenchmark':{'baseline':'freertos_microbenchmarks_clang', 
                   'baseline_mpu':'freertos_mpu_microbenchmarks_clang',
                   'kage':'microbenchmarks'}, 
            'coremark':{'baseline':'freertos_coremark_clang',
                    'baseline_mpu':'freertos_mpu_coremark',
                    'kage':'coremark'}}
DEVICE = 'demos/st/stm32l475_discovery/ac6'
OCD_CMD = 'program $PATH$ reset exit'
BUILD_CMD = \
    '-nosplash -application org.eclipse.cdt.managedbuilder.core.headlessbuild'\
    + ' -data $WORKSPACE$ -import $PROJPATH$ -cleanBuild $PROJECT$'

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
    # Optional System Workbench installation path
    parser.add_argument('--ac6', type=Path, default='~/Ac6/SystemWorkbench/eclipse')
    # Optional subset of configurations
    parser.add_argument('--configs', type=str, nargs='+', \
        default=['baseline', 'baseline_mpu', 'kage'])
    # Optional subset of benchmark programs
    parser.add_argument('--programs', type=str, nargs='+', \
        default=['microbenchmark', 'coremark'])
    # Print the output of subprocesses
    parser.add_argument('--verbose', action='store_true', default=False)
    # Get arguments
    args = parser.parse_args()

    # Set destinations of stdout and stderr according to argument
    if args.verbose:
        stdDst = subprocess.STDOUT
    else:
        stdDst = subprocess.DEVNULL

    # Generate project paths
    for program in args.programs:
        if not program in PROJECTS:
            print('ERROR: Unknown program ', program)
            exit()
        projProgram = PROJECTS[program]
        for config in args.configs:
            if not config in projProgram:
                print('ERROR: Unknown configuration ', config)
                exit()
            projectPath = Path(args.workspace).joinpath(projProgram[config])\
                .joinpath(DEVICE)
            # Import the project to System Workbench's workspace
            # and build the binaries
            ac6Arg = BUILD_CMD.replace('$WORKSPACE$', \
                    args.workspace.as_posix())
            ac6Arg = ac6Arg.replace('$PROJPATH$', projectPath.as_posix())
            ac6Arg = ac6Arg.replace('$PROJECT$', projProgram[config])
            ac6Arg = args.ac6.as_posix() + ' ' + ac6Arg
            subprocess.run(ac6Arg, shell=True, capture_output=False,
                           stderr=stdDst, stdout=stdDst, check=True)
            for configDir in projectPath.iterdir():
                if not configDir.is_dir():
                    continue
                if configDir.name[0] == '.':
                    continue
                print('Running ', program, ' ', config, ' ', configDir.name)
                # Execute OpenOCD on binary found in each build config
                binPath = configDir.joinpath(configDir.name + '.elf')
                ocdArg = OCD_CMD.replace('$PATH$', binPath.as_posix())
                subprocess.run([args.openocd, '-f', args.ocdcfg.as_posix(), '-c', \
                    ocdArg], stderr=stdDst, stdout=stdDst, check=True)
                print('Finished ', binPath.name)
                # Pause until user input
                input('Press Enter to continue')