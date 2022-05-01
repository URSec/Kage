#!/usr/bin/env python3

import argparse
import subprocess
from os import path
from pathlib import Path
from time import sleep

import serial
from colorama import Fore, Style
from elftools.elf.elffile import ELFFile

PROJECTS = {'microbenchmark': {'baseline': 'freertos_microbenchmarks_clang',
                               'baseline_mpu': 'freertos_mpu_microbenchmarks_clang',
                               'kage': 'microbenchmarks'},
            'coremark': {'baseline': 'freertos_coremark_clang',
                         'baseline_mpu': '',
                         'kage': 'coremark'}}
CONFIG_TERMS = {'mpu': 'FreeRTOS with MPU enabled',
                'baseline': 'FreeRTOS',
                'kage-no-silhouette': 'Kage\'s OS mechanisms',
                'kage-os-only': 'Kage\'s OS mechanisms',
                'kage': 'Kage', }
DEVICE = 'demos/st/stm32l475_discovery/ac6'
OCD_CMD = 'program $PATH$ reset exit'
BUILD_CMD = \
    '-nosplash --launcher.suppressErrors -application org.eclipse.cdt.managedbuilder.core.headlessbuild' \
    + ' -data $WORKSPACE$ -import $PROJPATH$ -cleanBuild $PROJECT$'

NUM_FREERTOS_MICROBENCHMARK_TESTS = 4
NUM_KAGE_MICROBENCHMARK_TESTS = 10
NUM_COREMARK_KAGE_NO_CACHE_TESTS = 6
NUM_COREMARK_TESTS = 3


# We use different configurations with unique names to enable different
# flags, in order to run different benchmarks of the same codebase.
# These configuration names are hard to understand, however, so we need
# to translate them.
def translateConfigName(name):
    translated_name = ''
    for configuration in CONFIG_TERMS:
        if configuration in name:
            translated_name = name.replace(configuration, (CONFIG_TERMS[configuration] + ': '))
            translated_name = translated_name.replace('-', ' ')
            break
    return translated_name


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
    parser.add_argument('--ocdcfg', type=Path,
                        default='/usr/share/openocd/scripts/board/st_b-l475e-iot01a.cfg',
                        help="Specify custom OpenOCD configuration path")
    # Optional System Workbench installation path
    parser.add_argument('--ac6', type=Path,
                        default='~/Ac6/SystemWorkbench/eclipse',
                        help="Custom path to System Workbench")
    # Optional subset of configurations
    parser.add_argument('--configs', type=str, nargs='+',
                        default=['baseline', 'baseline_mpu', 'kage'],
                        choices=['baseline', 'baseline_mpu', 'kage'],
                        help="Select the configurations to run (Note: baseline_mpu only contains microbenchmark and "
                             "no coremark)")
    # Optional subset of benchmark programs
    parser.add_argument('--programs', type=str, nargs='+',
                        default=['microbenchmark', 'coremark'],
                        choices=['microbenchmark', 'coremark'],
                        help="Select benchmark programs")
    # Print the output of subprocesses
    parser.add_argument('--verbose', action='store_true', default=False,
                        help="Print all compilation and flashing logs.")
    # 
    parser.add_argument('--disable_cache', action='store_true', default=False,
                        help="Disable instruction and data cache of the board (this option is only available when the "
                             "--programs argument contains only \"coremark\")")
    # (Optional) Write results to file
    parser.add_argument('--outfile', type=Path, required=False,
                        help="Write the results to a file")
    parser.add_argument('--build', action='store_true', default=False,
                        help='Runs make clean and build on all of the binaries. Needed for the first run.')
    parser.add_argument('--tries', type=int, default=3,
                        help="Number of tries when building a program. A value > 1 is recommended because the System Workbench's CMD interface is not very stable. Default: 3")
    # Get arguments
    args = parser.parse_args()

    # Set destinations of stdout and stderr according to argument
    if args.verbose:
        std_dst = subprocess.PIPE
        std_err = subprocess.STDOUT
    else:
        std_dst = subprocess.DEVNULL
        std_err = subprocess.DEVNULL

    # Initialize dict to store results
    perf_dict = {}
    size_dict = {}

    # Generate project paths
    for program in args.programs:
        if program not in PROJECTS:
            print(f'{Fore.RED}ERROR{Style.RESET_ALL}: Unknown program ', program)
            exit(1)
        if args.disable_cache and not program == 'coremark':
            print(f'{Fore.YELLOW}WARNING{Style.RESET_ALL}: --disable_cache option only supports coremark. Skipping ',
                  program)
            continue
        # Initialize dict to store results
        perf_dict[program] = {}
        size_dict[program] = {}

        projProgram = PROJECTS[program]
        for config in args.configs:
            if config not in projProgram:
                print(f'{Fore.RED}ERROR{Style.RESET_ALL}: Unknown configuration ', config)
                exit(1)
            if projProgram[config] == '':
                # No benchmark for this config and program combination, skipping
                continue
            projectPath = Path(args.workspace).joinpath(projProgram[config]).joinpath(DEVICE)
            # Initialize dict to store results
            perf_dict[program][config] = {}
            size_dict[program][config] = {}

            # Import the project to System Workbench's workspace and build the binaries
            if args.build:
                print('Compiling ', program, ' for ', config, '...')
                ac6Arg = BUILD_CMD.replace('$WORKSPACE$',
                                           args.workspace.as_posix())
                ac6Arg = ac6Arg.replace('$PROJPATH$', projectPath.as_posix())
                ac6Arg = ac6Arg.replace('$PROJECT$', projProgram[config])
                ac6Arg = args.ac6.as_posix() + ' ' + ac6Arg

                # Run the build process
                for i in range(args.tries):
                    with subprocess.Popen(ac6Arg, stdout=std_dst, stderr=std_err,
                                        bufsize=1, shell=True, text=True) as p:
                        while p.poll() is None:
                            if args.verbose:
                                for line in p.stdout:
                                    print(f'{Style.DIM}', line, end='')
                            sleep(.01)
                        print(f'{Style.RESET_ALL}', end='')
                        if p.returncode != 0:
                            # Building failed
                            if i < args.tries - 1:
                                print(f'{Fore.MAGENTA}WARNING{Style.RESET_ALL}: Command \'{ac6Arg}\' '
                                    f'returned status code {p.returncode}. Retrying...')
                            else:
                                print(f'{Fore.RED}ERROR{Style.RESET_ALL}: Command \'{ac6Arg}\' '
                                    f'returned status code {p.returncode}. Terminating benchmarks...')
                        else:
                            # Success
                            break

            # Get the build directories for the binaries and also removes hidden directories
            build_directories = [d for d in projectPath.iterdir() if d.is_dir() and d.name[0] != '.']

            # Check to make sure that the correct number of directories exist
            # WARNING, THESE VALUES ARE HARDCODED
            if program == 'microbenchmark':
                if config == 'kage':
                    if len(build_directories) != NUM_KAGE_MICROBENCHMARK_TESTS:
                        print(
                            f'{Fore.RED}ERROR{Style.RESET_ALL}: Binary folders at {projectPath} '
                            f'do not exist. Run the script with the \'--build\' flag')
                        exit(1)
                elif len(build_directories) != NUM_FREERTOS_MICROBENCHMARK_TESTS:
                    print(
                        f'{Fore.RED}ERROR{Style.RESET_ALL}: Binary folders at {projectPath} '
                        f'do not exist. Run the script with the \'--build\' flag')
                    exit(1)

            if program == 'coremark':
                # If the flag has been specified not to use cache, remove those directories from list
                if args.disable_cache:
                    build_directories = [d for d in build_directories if 'no-cache' in d.name]
                else:
                    build_directories = [d for d in build_directories if 'no-cache' not in d.name]

                if config == 'kage':
                    if args.disable_cache:
                        if len(build_directories) != NUM_COREMARK_TESTS:
                            print(f'{Fore.RED}ERROR{Style.RESET_ALL}: Unexpected number of folders')
                    elif len(build_directories) != NUM_COREMARK_KAGE_NO_CACHE_TESTS:
                        print(f'{Fore.RED}ERROR{Style.RESET_ALL}: Unexpected number of folders')
                elif len(build_directories) != NUM_COREMARK_TESTS:
                    print(
                        f'{Fore.RED}ERROR{Style.RESET_ALL}: Binary folders at {projectPath} '
                        f'do not exist. Run the script with the \'--build\' flag')
                    exit(1)

            for configDir in build_directories:
                print(f'Flashing and running {Fore.GREEN}', program, ' ',
                      translateConfigName(configDir.name), f'{Style.RESET_ALL}')
                # Execute OpenOCD on binary found in each build config
                binPath = configDir.joinpath(configDir.name + '.elf')

                # Check to make sure the binary exists
                if not path.isfile(binPath):
                    print(
                        f'{Fore.RED}ERROR{Style.RESET_ALL}: Binary {binPath} '
                        f'does not exist. Run the script with the \'--build\' flag')
                    exit(1)

                ocdArg = OCD_CMD.replace('$PATH$', binPath.as_posix())

                # Flash the binary asynchronously to immediately receive serial output
                with subprocess.Popen([args.openocd, '-f', args.ocdcfg.as_posix(), '-c', ocdArg],
                                      stdout=std_dst, stderr=std_err, bufsize=1, text=True) as p:
                    while p.poll() is None:
                        if args.verbose:
                            for line in p.stdout:
                                print(f'{Style.DIM}', line, end='')
                        sleep(.01)
                    print(f'{Style.RESET_ALL}', end='')
                    if p.returncode != 0:
                        print(
                            f'{Fore.RED}ERROR{Style.RESET_ALL}: Command \'{args.openocd} -f {args.ocdcfg.as_posix()} '
                            f'-c \"{ocdArg}\"\' returned status code {p.returncode}. Terminating benchmarks...')
                        exit(1)

                # Determine the human-readable configuration name
                confName = translateConfigName(configDir.name)
                # Compute code size
                with binPath.open('rb') as f:
                    elffile = ELFFile(f)
                    section = elffile.get_section_by_name('privileged_functions')
                    if section is None:
                        privileged_size = 0
                    else:
                        privileged_size = section.data_size

                    section = elffile.get_section_by_name('freertos_system_calls')
                    if section is None:
                        syscallSize = 0
                    else:
                        syscallSize = section.data_size
                    textSize = elffile.get_section_by_name('.text').data_size
                    # Calculate total trusted and untrusted size
                    if 'baseline' in config:
                        # Everything is trusted in FreeRTOS and FreeRTOS with MPU
                        trusted = privileged_size + syscallSize + textSize
                        untrusted = 0
                    else:
                        trusted = privileged_size
                        untrusted = syscallSize + textSize

                    # Open serial port with 2 minute timeout. This loop ends when the timeout is reached.
                    # or when the last line is read
                    with serial.Serial('/dev/ttyACM0', 115200, timeout=120) as ser:
                        while True:
                            # Sleep for just a millisecond to give a slight buffer
                            sleep(.001)

                            try:
                                line = ser.readline().decode()
                                if args.verbose:
                                    print(f'{Style.DIM}', line, end='')
                            except UnicodeDecodeError as ude:
                                print(
                                    f'{Style.RESET_ALL}{Fore.YELLOW}WARNING{Style.RESET_ALL}: '
                                    f'Decoding error, skipping line')
                                print(ude)
                                continue

                            if len(line) == 0:
                                # timeout
                                print(f'\b{Style.RESET_ALL}{Fore.YELLOW}TIMEOUT REACHED{Style.RESET_ALL}: ', end='')
                                break

                            # Each benchmark has different output format, so do a manual matching here.
                            if 'stream-buffer' in configDir.name:
                                # Stream buffer microbenchmark
                                if 'Creating stream buffer' in line:
                                    # Stream buffer creation
                                    t = int(line.split(': ')[1].replace('\n', '').replace('\r', ''))
                                    perf_dict[program][config][confName + ': create'] = t
                                if 'Received unsigned 9 from stream buffer' in line:
                                    # Stream buffer send and receive
                                    t = int(line.split(': ')[1].replace('\n', '').replace('\r', ''))
                                    perf_dict[program][config][confName + ': send and receive'] = t
                                    size_dict[program][config][confName] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                if 'Started Microbenchmark Low Priority Task' in line:
                                    break
                            if 'queue' in configDir.name:
                                # Queue microbenchmark
                                if 'Creating queue' in line:
                                    # Queue creation
                                    t = int(line.split(': ')[1].replace('\n', '').replace('\r', ''))
                                    perf_dict[program][config][confName + ': create'] = t
                                if 'Received unsigned 9 from queue' in line:
                                    # Queue send and receive
                                    t = int(line.split(': ')[1].replace('\n', '').replace('\r', ''))
                                    perf_dict[program][config][confName + ': send and receive'] = t
                                    size_dict[program][config][confName] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                if 'Started Microbenchmark Low Priority Task' in line:
                                    break
                            if 'exception-dispatcher' in configDir.name:
                                # Exception microbenchmark
                                if 'DIV_BY_0' in line:
                                    t = int(line.split(': 0 ')[1].split(' cycles')[0])
                                    perf_dict[program][config][confName.replace('dispatcher', '')] = t
                                    size_dict[program][config][confName.replace('dispatcher', '')] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                if 'Started Microbenchmark Low Priority Task' in line:
                                    break
                            if 'context-switch' in configDir.name:
                                # Context switch microbenchmark
                                if 'Context Switch cycle' in line:
                                    t = int(line.split(': ')[1].split(' cycles')[0])
                                    perf_dict[program][config][confName] = t
                                    size_dict[program][config][confName] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                    break
                            if 'secure-api' in configDir.name:
                                # Secure API microbenchmark
                                if 'MPU checks' in line:
                                    t = int(line.split(': ')[1].split(' cycles')[0])
                                    perf_dict[program][config][confName + ': MPU region configuration'] = t
                                if 'xVerifyTCB' in line:
                                    t = int(line.split(': ')[1].replace('\r', '').replace('\n', ''))
                                    perf_dict[program][config][confName + ': task control block'] = t
                                if 'xVerifyUntrustedData' in line:
                                    t = int(line.split(': ')[1].replace('\r', '').replace('\n', ''))
                                    perf_dict[program][config][confName + ': other pointers'] = t
                                if 'Exception priority' in line:
                                    t = int(line.split(': ')[1].replace('\r', '').replace('\n', ''))
                                    perf_dict[program][config][confName + ': exception priority'] = t
                                    size_dict[program][config][confName] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                    break
                            if 'coremark' in configDir.name:
                                # CoreMark
                                if 'Iterations/Sec' in line:
                                    t = float(line.split(': ')[1].replace('\n', ''))
                                    perf_dict[program][config][confName] = t
                                    size_dict[program][config][confName] = \
                                        {'trusted': trusted, 'untrusted': untrusted}
                                if 'CoreMark 1.0' in line:
                                    break
                        # While loop exited
                        print(f'{Style.RESET_ALL}{Fore.GREEN}All results read{Style.RESET_ALL}')

    # Generate result string
    resultStr = "Performance results:\n"
    for program in perf_dict:
        resultStr += (program + ':\n')
        for config in perf_dict[program]:
            perfDictPart = perf_dict[program][config]
            # Sort the order of benchmarks to print
            benchList = sorted(list(perfDictPart.keys()))
            for bench in benchList:
                resultStr += (bench.ljust(65) + str(perfDictPart[bench]))
                if program == 'coremark':
                    resultStr += ' iter/sec\n'
                else:
                    resultStr += ' cycles\n'
    resultStr += '\nCode size results (bytes)\n'
    for program in size_dict:
        resultStr += (program + ':\n')
        for config in size_dict[program]:
            sizeDictPart = size_dict[program][config]
            # Sort the order of benchmarks
            benchList = sorted(list(sizeDictPart.keys()))
            for bench in benchList:
                resultStr += (bench.ljust(60) + str(sizeDictPart[bench]) + '\n')
    print(resultStr)

    if args.outfile is not None:
        with args.outfile.open('w') as file:
            file.write(resultStr)
            print("Results stored to ", args.outfile.as_posix())
