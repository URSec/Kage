# Kage

Kage is a software defense against control-flow hijacking attacks on embedded
ARM systems running real-time operating system. Our implementation includes the
compiler, the instrumented FreeRTOS-based real-time OS, and the binary code
scanner. We tested our implementation on an STM32L475 (B-L475E-IOT01A) 
Discovery kit.

For the details of Kage, check [our
paper](https://www.usenix.org/conference/usenixsecurity22/presentation/du).

## Setting Up Kage
1. Install [OpenSTM32 System Workbench](https://www.openstm32.org/HomePage)
2. Install LLVM Clang compiler. 
3. Install `arm-none-eabi` cross-compile tools. For Arch Linux, install the
`arm-none-eabi-gcc` and `arm-none-eabi-binutils` packages. For Fedora, install
`arm-none-eabi-gcc-cs`.
4. Enter the `build` directory.
4. Build our LLVM-based compiler using the build script `build.llvm.sh`.
5. Build the instrumented newlib C library using the build script
`build.newlib.sh`.
6. Build the instrumented compiler-rt using the build script
`build.compiler.rt.sh`.
7. Install the `pyelftools` Python module, required by our binary code scanner:
`pip install pyelftools`.
8. Open the System Workbench IDE and select the `workspace` directory as the
workspace. Since FreeRTOS is built along with the application code,
our projects include both our instrumented FreeRTOS and applications we used
during our evaluation (CoreMark and microbenchmarks). Our workspace module also
includes benchmark programs running on unmodified FreeRTOS (projects with the
`freertos_` prefix).
9. By default, System Workbench will not automatically import the projects.
Therefore, manually import the projects you wish to use by selecting
`File -> Open Projects from File System`. In each project directory,
select the `demos/st/stm32l475_discovery/ac6` directory for the IDE to find
the project for the specific board model.

## Contacts
Yufei Du: yufeidu@cs.unc.edu

Zhuojia Shen: zshen10@cs.rochester.edu

Komail Dharsee: kdharsee@cs.rochester.edu

Jie Zhou: jzhou41@cs.rochester.edu

John Criswell: criswell@cs.rochester.edu

Robert J. Walls: rjwalls@wpi.edu