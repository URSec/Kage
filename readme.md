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
2. Use the build scripts (`build.llvm.sh`, `build.compiler.rt.sh`,
`build.newlib.sh`) located in the `build` directory to build the LLVM-based
compiler, the compiler-rt library, and the newlib C library.
3. Install the `pyelftools` Python module, required by our binary code scanner:
`pip install pyelftools`.
4. Open the System Workbench IDE and select the `workspace` directory as the
workspace. Since FreeRTOS is built along with the application code,
our projects include both our instrumented FreeRTOS and applications we used
during our evaluation (CoreMark and microbenchmarks). Our workspace module also
includes benchmark programs running on unmodified FreeRTOS (projects with the
`freertos_` prefix).

## Contacts
Yufei Du: yufeidu@cs.unc.edu

Zhuojia Shen: zshen10@cs.rochester.edu

Komail Dharsee: kdharsee@cs.rochester.edu

Jie Zhou: jzhou41@cs.rochester.edu

John Criswell: criswell@cs.rochester.edu

Robert J. Walls: rjwalls@wpi.edu