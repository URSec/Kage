# Kage

Kage is a software defense against control-flow hijacking attacks on embedded
ARM systems running real-time operating system. Our implementation includes the
compiler, the instrumented FreeRTOS-based real-time OS, and the binary code
scanner. We tested our implementation on an STM32L475 (B-L475E-IOT01A) 
Discovery kit.

For the details of Kage, check [our
paper](https://www.usenix.org/conference/usenixsecurity22/presentation/du).

## Setting Up Kage
NOTE: We tested Kage on Fedora 35 and Arch Linux (April 2022). If you run
into unknown errors on other OS or distributions, please consider trying
on Fedora 35.
1. Install [OpenSTM32 System Workbench](https://www.openstm32.org/HomePage)
2. Install LLVM Clang compiler. 
3. Install `arm-none-eabi` cross-compile tools. For Arch Linux, install the
`arm-none-eabi-gcc` and `arm-none-eabi-binutils` packages. For Fedora, install
`arm-none-eabi-gcc-cs`.
4. Clone this repo using `git clone --recurse-submodules https://github.com/URSec/Kage.git`. If you forget to include 
the `--recurse-submodules` flag, you can run `git submodule update --init` to download the submodules.
5. Enter the `build` directory.
6. Build our LLVM-based compiler using the build script `build.llvm.sh`.
7. Build the instrumented newlib C library using the build script
`build.newlib.sh`.
8. Build the instrumented compiler-rt using the build script
`build.compiler.rt.sh`.
9. Install the `pyelftools` Python module, required by our binary code scanner:
`pip install pyelftools`.
10. Open the System Workbench IDE and select the `workspace` directory as the
workspace. Since FreeRTOS is built along with the application code,
our projects include both our instrumented FreeRTOS and applications we used
during our evaluation (CoreMark and microbenchmarks). Our workspace module also
includes benchmark programs running on unmodified FreeRTOS (projects with the
`freertos_` prefix). Beside our benchmark projects, we also include an empty
template project, `template`, that includes only the Kage RTOS and two empty
demo tasks, each with only a print statement.
11. By default, System Workbench will not automatically import the projects.
Therefore, manually import the projects you wish to use by selecting
`File -> Open Projects from File System`. In each project directory,
select the `demos/st/stm32l475_discovery/ac6` directory for the IDE to find
the project for the specific board model. If you would like to run your own
application code on Kage, use the `template` project, which contains two empty
tasks in `sil_demo.c`. You can write your application code in the same tasks
or create new tasks. Note that if you increase the number of tasks running on
the board, you need to also update `configTOTAL_TASKS` in
`config_files/FreeRTOSConfig.h`. Since our implementation uses parallel shadow
stack, on the STM32L475 Discovery board with 128KB of RAM, you can create up
to 3 application tasks due to memory consumption.

## Reproducing experiment results using automated script
To easily reproduce our experiments, we provide an automated script
`scripts/run-benchmarks.py` to build the binaries and flash each one to
the discovery board. The script requires Python 3.5 or later.
1. Follow step 1-8 in Setting Up Kage.
2. Install OpenOCD.
3. Install the `colorama` and `pyserial` Python modules, required by the
automated script: `pip install colorama pyserial`.
4. Enter the `scripts` directory and run `python run-benchmarks.py --build`.
To learn about the script's optional arguments, run
`python run-benchmarks.py -h`. 
Depending on your version of board, you may need to include the OpenOCD config file for that board. As an example,
`--ocdcfg /usr/share/openocd/scripts/board/stm32l4discovery.cfg` will ensure OpenOCD can connect to the STM32L475 Discovery.
5. If you want to reproduce the CoreMark experiments without caching, run
`python run-benchmarks.py --build --disable_cache`.

In addition to the performance and code size experiments, we also provide
a script that uses ROPGadget to find gadgets of a binary file. Given a
binary file, the script can find all gadgets, reachable gadgets when Kage
is applied, and the number of privileged stores (i.e., regular store
instructions and push instructions) in reachable gadgets. In the paper,
we also report the number of stitchable gadgets (see Section 6.2 and Table
7). However, we had to manually inspect the reachable gadgets to determine
if they are actually stitchable under Kage's return address integrity
guarantee. We provide a script `find_stitchable_gadgets.py` that filters
out gadgets that are not stitchable even without Kage. For the
rest of the gadgets, the user needs to manually inspect each of them to
see if it is stitchable.

To reproduce security evaluation:
1. Follow the above steps to build and run the benchmark programs in order to
generate the required binary files.
2. If not already, enter the `Kage/scripts` directory.
3. Run the `run-gadgets.py` script with the following arguments to analyze
the FreeRTOS (baseline) binary of CoreMark with 3 threads:
`--preset --mode freertos`. Optionally, the script can write the list of
all gadgets (using `--out_total <path>` argument) and the list of reachable
gadgets (using `--out_reachable <path>`) for further inspection.
4. Run the `run-gadgets.py` script with the following arguments to analyze
the Kage binary of CoreMark with 3 threads:
`--preset --mode kage`. Likewise, the script can write the list of all
gadgets and reachable gadgets using the same arguments as the previous step.
5. (Only accurate for FreeRTOS binaries) If you have the output file of
reachable gadgets, you can run the `find_stitchable_gadgets.py` script to
find the list of stitchable gadgets for the FreeRTOS binary using the
following argument: `-f <path>`. Note that this script prints the list
of gadgets directly to the terminal.


## Troubleshooting
1. The command line interface of System Workbench IDE is unstable and may throw
    random errors occasionally. To circumvent this issue, our benchmark script
    provides an option `--tries` to automatically re-run System Workbench on
    error. By default, the benchmark script will try 3 times.
2. If System Workbench still fails to build a program after many tries, please
    navigate to the `workspace` directory and use `git status` to check file
    integrity. On rare occasions, System Workbench's command line interface may
    corrupt the configuration files when running on unsupported OS. If you see
    that any `.project` or `.cproject` files are modified, please consider
    switching to a Linux distribution we tested: Fedora 35 and Arch Linux
    (April 2022).

## Implementation Notes to Developers
The exception dispatcher is a proof of concept and will not be automatically added to developer created interrupts.
To ensure security guarantee 4, developers must wrap their interrupt handlers with an exception dispatching function.
An example dispatcher is included in port.c
[(GitHub link)](https://github.com/URSec/Kage-FreeRTOS/blob/8b096c9ab1ac32ebaf6c4d54c5905c247ffd92cc/coremark/lib/FreeRTOS/portable/GCC/ARM_CM4_MPU/port.c#L353)
[(repo link)](./workspace/coremark/lib/FreeRTOS/portable/GCC/ARM_CM4_MPU/port.c).

Shadow Stacks are offset at 4092 bytes defined in portmacro.h 
[(GitHub link)](https://github.com/URSec/Kage-FreeRTOS/blob/8b096c9ab1ac32ebaf6c4d54c5905c247ffd92cc/coremark/lib/FreeRTOS/portable/GCC/ARM_CM4_MPU/portmacro.h#L59)
[(repo link)](./workspace/coremark/lib/FreeRTOS/portable/GCC/ARM_CM4_MPU/portmacro.h)
due to the requirement of encoding four of arm add instructions having immediate offset values inside the range 0-4095. 4092 is the highest 
4 byte multiple in this range.

If you add additional tests to microbenchmarks, coremark, or the template folder, you will need to modify
the `run-benchmarks.py` script to accommodate running your benchmark test. You will need to update the NUM\_\*\_TESTS 
constants.

## Contacts
Yufei Du: yufeidu@cs.unc.edu

Zhuojia Shen: zshen10@cs.rochester.edu

Komail Dharsee: kdharsee@cs.rochester.edu

Jie Zhou: jzhou41@cs.rochester.edu

John Criswell: criswell@cs.rochester.edu

Robert J. Walls: rjwalls@wpi.edu
