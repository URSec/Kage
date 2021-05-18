#!/usr/bin/env python3

import argparse

from elftools.elf.elffile import ELFFile


class CodeScanner(object):
    SECURE_APIS = [
        'xTaskCreateRestricted',
        'vTaskFinishInit',
        'vTaskDelete',
        'vTaskDelayUntil',
        'vTaskDelay',
        'vTaskPrioritySet',
        'vTaskSuspend',
        'vTaskResume',
        'vTaskAllocateMPURegions',
        'ulTaskNotifyTake',
        'xTaskNotifyWait',
        'xTaskGenericNotify',
        'xTaskNotifyStateClear',

        'vTaskMissedYield',
        'xTaskPriorityInherit',
        'xTaskPriorityDisinherit',
        'xTaskPriorityDisinheritAfterTimeout',
        'pvTaskIncrementMutexHeldCount',
        'vTaskSuspendAll',
        'xTaskResumeAll',
        'vTaskPlaceOnEventList',
        'vTaskPlaceOnEventListRestricted',
        'vTaskPlaceOnUnorderedEventList',
        'xTaskRemoveFromEventList',
        'vTaskRemoveFromUnorderedEventList',

        'xTaskResumeFromISR',
        'xTaskGenericNotifyFromISR',
        'vTaskNotifyGiveFromISR',

        'vPortEnterCritical',
        'vPortExitCritical',
    ]

    def __init__(self, binary, sections, unaligned):
        self.binary = binary
        self.sections = sections
        self.unaligned = unaligned

        self.__elf = ELFFile(open(binary, 'rb'))
        self.__privileged_section = self.__elf.get_section_by_name('privileged_functions')
        assert self.__privileged_section, 'No section named privileged_functions'
        for section in self.sections:
            text = self.__elf.get_section_by_name(section)
            assert text, 'Section does not exist: {:s}'.format(section)
            assert text.data_size % 2 == 0, 'Odd code section size: {:s}'.format(section)

        # Construct a map of PC -> function name
        symtab = self.__elf.get_section_by_name('.symtab')
        assert symtab, 'Stripped binary not supported'
        self.__funcs = {}
        for sym in symtab.iter_symbols():
            if sym.entry['st_info']['type'] == 'STT_FUNC':
                self.__funcs[sym.entry['st_value'] & ~0x1] = {
                    'name': sym.name,
                    'section': self.__elf.get_section(sym.entry['st_shndx']).name,
                }

    def scan(self):
        for section in self.sections:
            text = self.__elf.get_section_by_name(section)

            i = 0
            while i < text.data_size:
                byte0 = text.data()[i]
                byte1 = text.data()[i + 1]
                inst = (byte1 << 8) | byte0
                addr = text.header['sh_addr'] + i

                # Determine if it's a Thumb or Thumb-2 instruction
                prefix = inst >> 11
                if prefix == 0b11101 or prefix == 0b11110 or prefix == 0b11111:
                    assert i + 2 < text.data_size, 'Truncated Thumb-2 instruction: {:s}'.format(section)

                    byte2 = text.data()[i + 2]
                    byte3 = text.data()[i + 3]
                    inst2 = (byte3 << 8) | byte2
                    inst = (inst << 16) | inst2

                    # Skip our CFI label
                    if inst == 0xf871f870:
                        i += 4
                        continue

                    self.__scan_4byte_inst(inst, addr)
                    if self.unaligned:
                        self.__scan_2byte_inst(inst2, addr + 2)
                    i += 4
                else:
                    self.__scan_2byte_inst(inst, addr)
                    i += 2

    def __scan_2byte_inst(self, inst, addr):
        # Scan for CPS
        cps_opcode = 0xb660
        cps_opcode_mask = 0xffec
        if (inst & cps_opcode_mask) == cps_opcode:
            print('[CS] CPS at 0x{:x}'.format(addr))

    def __scan_4byte_inst(self, inst, addr):
        # Scan for MSR
        msr_opcode = 0xf3808000
        msr_opcode_mask = 0xfff0f300
        if (inst & msr_opcode_mask) == msr_opcode:
            print('[CS] MSR at 0x{:x}'.format(addr))

        # Scan for BL (normal call) and B (tail call)
        bl_opcode = 0xf000d000
        bl_opcode_mask = 0xf800d000
        b_opcode = 0xf0009000
        b_opcode_mask = 0xf800d000
        if (inst & bl_opcode_mask) == bl_opcode or (inst & b_opcode_mask) == b_opcode:
            imm11 = inst & 0x7ff
            imm10 = (inst >> 16) & 0x3ff
            j2 = (inst >> 11) & 0x1
            j1 = (inst >> 13) & 0x1
            s = (inst >> 26) & 0x1
            opcode = 'BL' if (inst & bl_opcode_mask) == bl_opcode else 'B'

            i1 = not(j1 ^ s)
            i2 = not(j2 ^ s)
            offset = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
            # Sign extend with sign bit 25
            offset = (offset & ((1 << 24) - 1)) - (offset & (1 << 24))

            dest = addr + 4 + offset
            priv_start = self.__privileged_section.header['sh_addr']
            priv_end = priv_start + self.__privileged_section.data_size
            if dest >= priv_start and dest < priv_end:
                assert dest in self.__funcs, 'Jump to the middle of trusted function'
                if self.__funcs[dest]['name'] not in CodeScanner.SECURE_APIS:
                    print('[CS] {:s} {:s} at 0x{:x}'.format(opcode, self.__funcs[dest]['name'], addr))


def main():
    # Construct a CLI argument parser
    parser = argparse.ArgumentParser(description='Kage Code Scanner')
    parser.add_argument('-s', '--section', action='append', default=[],
                        help='name of the code section to scan')
    parser.add_argument('-u', '--unaligned', action='store_true',
                        help='scan unaligned instructions as well')
    parser.add_argument('binary', help='path to the binary executable')

    # Parse CLI arguments
    args = parser.parse_args()
    binary = args.binary
    if not args.section:
        args.section.append('.text')
    sections = set(args.section)
    unaligned = args.unaligned

    # Construct and run a code scanner
    scanner = CodeScanner(binary, sections, unaligned)
    scanner.scan()


if __name__ == '__main__':
    main()
