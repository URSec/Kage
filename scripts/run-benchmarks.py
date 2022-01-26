#!/usr/bin/env python3

import argparse
from colorama import Back, Fore, Style
from pathlib import Path
from elftools.elf.elffile import ELFFile
import serial
import subprocess
from sys import stderr

PROJECTS = {'microbenchmark':{'baseline':'freertos_microbenchmarks_clang', 
                   'baseline_mpu':'freertos_mpu_microbenchmarks_clang',
                   'kage':'microbenchmarks'}, 
            'coremark':{'baseline':'freertos_coremark_clang',
                    'baseline_mpu':'',
                    'kage':'coremark'}}
CONFIG_TERMS = {'mpu': 'FreeRTOS with MPU enabled',
         'baseline': 'FreeRTOS',
         'kage-no-silhouette': 'Kage\'s OS mechanisms',
         'kage-os-only': 'Kage\'s OS mechanisms',
         'kage': 'Kage',}
DEVICE = 'demos/st/stm32l475_discovery/ac6'
OCD_CMD = 'program $PATH$ reset exit'
BUILD_CMD = \
    '-nosplash -application org.eclipse.cdt.managedbuilder.core.headlessbuild'\
    + ' -data $WORKSPACE$ -import $PROJPATH$ -cleanBuild $PROJECT$'

# We use different configurations with unique names to enable different
# flags, in order to run different benchmarks of the same codebase.
# These configuration names are hard to understand, however, so we need
# to translate them.
def translateConfigName(name):
    for config in CONFIG_TERMS:
        if config in name:
            translatedName = name.replace(config, (CONFIG_TERMS[config] + ': '))
            translatedName = translatedName.replace('-', ' ')
            break
    return translatedName

# Main routine
if __name__ == "__main__":
    # Argparse
    parser = argparse.ArgumentParser()
    # Optional custom workspace path
    parser.add_argument('--workspace', type=Path, default=Path('../workspace'),
        help="Specify path to the System Workbench workspace")
    # Optional custom OpenOCD binary path
    parser.add_argument('--openocd', type=str, default='openocd',
        help="Specify custom path of OpenOCD")
    # Optional OpenOCD configuration path
    parser.add_argument('--ocdcfg', type=Path, \
        default='/usr/share/openocd/scripts/board/st_b-l475e-iot01a.cfg',
        help="Specify custom OpenOCD configuration path")
    # Optional System Workbench installation path
    parser.add_argument('--ac6', type=Path,
        default='~/Ac6/SystemWorkbench/eclipse',
        help="Custom path to System Workbench")
    # Optional subset of configurations
    parser.add_argument('--configs', type=str, nargs='+', \
        default=['baseline', 'baseline_mpu', 'kage'],
        choices=['baseline', 'baseline_mpu', 'kage'],
        help="Select the configurations to run (Note: baseline_mpu only contains microbenchmark and no coremark)")
    # Optional subset of benchmark programs
    parser.add_argument('--programs', type=str, nargs='+', \
        default=['microbenchmark', 'coremark'],
        choices=['microbenchmark', 'coremark'],
        help="Select benchmark programs")
    # Print the output of subprocesses
    parser.add_argument('--verbose', action='store_true', default=False,
        help="Print all compilation and flashing logs.")
    # Do not print code size results
    parser.add_argument('--no_code_size', action='store_true', default=False,
        help="Only run performance benchmark without showing code size.")
    # 
    parser.add_argument('--disable_cache', action='store_true', default=False,
        help="Disable instruction and data cache of the board (this option is only available when the --programs argument contains only \"coremark\")")
    # Get arguments
    args = parser.parse_args()

    # Set destinations of stdout and stderr according to argument
    if args.verbose:
        stdDst = subprocess.STDOUT
    else:
        stdDst = subprocess.DEVNULL
    
    # Initialize dict to store results
    perfDict = {}
    sizeDict = {}
    
    # Initialize serial interface with 2 minutes of timeout
    with serial.Serial('/dev/ttyACM0', 115200, timeout=120) as ser:
        # Generate project paths
        for program in args.programs:
            if not program in PROJECTS:
                print('ERROR: Unknown program ', program)
                exit()
            if args.disable_cache and not program == 'coremark':
                print('WARNING: --disable_cache option only supports coremark. Skipping ', program)
                continue
            # Initialize dict to store results
            perfDict[program] = {}
            sizeDict[program] = {}

            projProgram = PROJECTS[program]
            for config in args.configs:
                if not config in projProgram:
                    print('ERROR: Unknown configuration ', config)
                    exit()
                if projProgram[config] == '':
                    # No benchmark for this config and program combination,
                    # skipping
                    continue
                projectPath = Path(args.workspace).joinpath(projProgram[config])\
                    .joinpath(DEVICE)
                # Initialize dict to store results
                perfDict[program][config] = {}
                sizeDict[program][config] = {}
                # Import the project to System Workbench's workspace
                # and build the binaries
                print('Compiling ', program, ' for ', config, '...')
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
                    # Only run configs without cache when requested.
                    # Also, when requested to run without cache, skip configs
                    # with cache. 
                    if ('no-cache' in configDir.name) != (args.disable_cache):
                        continue
                    print(f'Flashing {Fore.GREEN}', program, ' ',
                        translateConfigName(configDir.name), f'{Style.RESET_ALL}')
                    # Execute OpenOCD on binary found in each build config
                    binPath = configDir.joinpath(configDir.name + '.elf')
                    ocdArg = OCD_CMD.replace('$PATH$', binPath.as_posix())
                    # Flash the binary asynchronously to immediate receive serial
                    # output
                    subprocess.run([args.openocd, '-f', args.ocdcfg.as_posix(), '-c', \
                        ocdArg], stderr=stdDst, stdout=stdDst)
                    # Determine the human-readable configuration name
                    confName = translateConfigName(configDir.name)
                    # Compute code size
                    with binPath.open('rb') as file:
                        elffile = ELFFile(file)
                        section = elffile.get_section_by_name(\
                            'privileged_functions')
                        if section is None:
                            privSize = 0
                            # print('No privileged_functions section')
                        else:
                            privSize = section.data_size
                            # print('privileged_functions: ', privSize)
                        section = elffile.get_section_by_name(\
                            'freertos_system_calls')
                        if section is None:
                            syscallSize = 0
                            # print('No freertos_system_calls section')
                        else:
                            syscallSize = section.data_size
                            # print('freertos_system_calls: ', syscallSize)
                        textSize = elffile.get_section_by_name(\
                            '.text').data_size
                        # print('.text: ', textSize)
                        # Calculate total trusted and untrusted size
                        if 'baseline' in config:
                            # Everything is trusted in FreeRTOS and
                            # FreeRTOS with MPU
                            trusted = privSize + syscallSize + textSize
                            untrusted = 0
                        else:
                            trusted = privSize
                            untrusted = syscallSize + textSize
                    # Read output
                    while True:
                        # Read output
                        line = ser.readline().decode('utf-8')
                        if len(line) == 0:
                            # timeout
                            print("ERROR: Timeout waiting for results from the board.")
                            exit(1)
                        # Each benchmark has different output format, so do a
                        # manual matching here.
                        if 'stream-buffer' in configDir.name:
                            # Stream buffer microbenchmark
                            if 'Creating stream buffer' in line:
                                # Stream buffer creation
                                t = int(line.split(': ')[1].replace('\n', '')\
                                    .replace('\r', ''))
                                perfDict[program][config][confName + ': create'] = t
                            if 'Received unsigned 9 from stream buffer' in line:
                                # Stream buffer send and receive
                                t = int(line.split(': ')[1].replace('\n', '')\
                                    .replace('\r', ''))
                                perfDict[program][config][confName + ': send and receive'] = t
                                sizeDict[program][config][confName] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
                        if 'queue' in configDir.name:
                            # Queue microbenchmark
                            if 'Creating queue' in line:
                                # Queue creation
                                t = int(line.split(': ')[1].replace('\n', '')\
                                    .replace('\r', ''))
                                perfDict[program][config][confName + ': create'] = t
                            if 'Received unsigned 9 from queue' in line:
                                # Queue send and receive
                                t = int(line.split(': ')[1].replace('\n', '')\
                                    .replace('\r', ''))
                                perfDict[program][config][confName + ': send and receive'] = t
                                sizeDict[program][config][confName] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
                        if 'exception-dispatcher' in configDir.name:
                            # Exception microbenchmark
                            if 'DIV_BY_0' in line:
                                t = int(line.split(': 0 ')[1].split(' cycles')[0])
                                perfDict[program][config][confName.replace('dispatcher', '')] = t
                                sizeDict[program][config][confName.replace('dispatcher', '')] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
                        if 'context-switch' in configDir.name:
                            # Context switch microbenchmark
                            if 'Context Switch cycle' in line:
                                t = int(line.split(': ')[1].split(' cycles')[0])
                                perfDict[program][config][confName] = t
                                sizeDict[program][config][confName] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
                        if 'secure-api' in configDir.name:
                            # Secure API microbenchmark
                            if 'MPU checks' in line:
                                t = int(line.split(': ')[1].split(' cycles')[0])
                                perfDict[program][config]\
                                    [confName + ': MPU region configuration'] = t
                            if 'xVerifyTCB' in line:
                                t = int(line.split(': ')[1].replace('\r', '')\
                                    .replace('\n', ''))
                                perfDict[program][config]\
                                        [confName + ': task control block'] = t
                            if 'xVerifyUntrustedData' in line:
                                t = int(line.split(': ')[1].replace('\r', '')\
                                    .replace('\n', ''))
                                perfDict[program][config]\
                                        [confName + ': other pointers'] = t
                            if 'Exception priority' in line:
                                t = int(line.split(': ')[1].replace('\r', '')\
                                    .replace('\n', ''))
                                perfDict[program][config]\
                                        [confName + ': exception priority'] = t
                                sizeDict[program][config][confName] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
                        if 'coremark' in configDir.name:
                            # CoreMark
                            if 'Iterations/Sec' in line:
                                t = float(line.split(': ')[1].replace('\n', ''))
                                perfDict[program][config][confName] = t
                                sizeDict[program][config][confName] = \
                                    {'trusted':trusted, 'untrusted':untrusted}
                                break
        print("Performance results:")
        for program in perfDict:
            print(program, ':')
            for config in perfDict[program]:
                perfDictPart = perfDict[program][config]
                for bench in perfDictPart:
                    if program == 'coremark':
                        print(bench, ':\t\t', perfDictPart[bench], ' iter/sec')
                    else:
                        print(bench, ':\t\t', perfDictPart[bench], ' cycles')
        print("\n\nCode size results:")
        for program in sizeDict:
            print(program, ':')
            for config in sizeDict[program]:
                sizeDictPart = sizeDict[program][config]
                for bench in sizeDictPart:
                    print(bench, ': \t', sizeDictPart[bench])
