"""CPU functionality."""

import sys
import time
import msvcrt

class CPU:
    """Main CPU class."""

    def __init__(self, register_count = 9, calloc_size = 10000, DEBUG = False):
        """Construct a new CPU."""
        self.reg = [0b00000000] * register_count # Flag register is 7, IS register is 6, IM register is 5
        self.ram = [0b00000000] * calloc_size

        self.instruction_map = {
            0b00000001: self.HLT,
            0b01000111: self.PRN,

            0b01010010: self.INT,
            0b00010011: self.IRET,

            0b10000010: self.LDI,
            0b01000101: self.PUSH,
            0b01000110: self.POP,

            0b01010100: self.JMP,
            0b01010101: self.JEQ,
            0b01010110: self.JNE,
            0b01010000: self.CALL,
            0b00010001: self.RET,

            0b10101010: self.ALU_OP1, # OR
            0b01101001: self.ALU_OP1, # NOT

            0b10100000: self.ALU_OP2, # ADD
            0b10100010: self.ALU_OP2, # MUL
            0b10100100: self.ALU_OP2, # MOD
            
            0b10100111: self.ALU_OP2, # CMP
            0b10101000: self.ALU_OP2, # AND
            0b10101011: self.ALU_OP2, # XOR
            0b10101100: self.ALU_OP2, # SHL
            0b10101101: self.ALU_OP2, # SHR

            0b11101110: self.ALU_OP3, # ADDI
        }

        self.ALU_OPS = {
            0b10100000: "ADD",
            0b10100010: "MUL",
            0b10100100: "MOD",
            0b10100111: "CMP",
            0b10101000: "AND",
            0b10101010: "OR" ,
            0b10101011: "XOR",
            0b01101001: "NOT",
            0b10101100: "SHL",
            0b10101101: "SHR",
            0b11101110: "ADDI",
        }

        self.INTERRUPT_VECTORS = {
            0b00000001: 0b11101011,
            0b00000010: 0b11101100,
        }

        self.ram_top = calloc_size - 1
        self.stack_last = 0
        self.instruction = 0
        self.program_end = 0
        self.disable_interrupts = False
        self.active = False
        self.DEBUG = DEBUG

    def load(self, file_name):
        """Load a program into memory."""
        address = 0
        break_keys = { ' ', '\n', '#' }

        def parse_line(line):
            if len(line) == 0 or line[0] in break_keys:
                return [False]

            code = ''
            
            for c in line:
                if c in break_keys:
                    break

                code += c

            if len(code) != 8:
                raise Exception(f"Program load failed, instruction was not 8 bits: {code}")

            return [True, int(code, base=2)]

        with open(file_name, "r") as file:
            for line in file:
                return_values = parse_line(line)

                if return_values[0] == True:
                    self.ram[address] = return_values[1]
                    address += 1

        self.program_end = address

    def ram_read(self, position):
        if position < 0 or position >= len(self.ram):
            print("SEG FAULT NO POS")
            sys.exit(1)

        return self.ram[position]

    def ram_write(self, position, binary_value):
        if position < 0 or position >= len(self.ram):
            print("SEG FAULT NO POS")
            sys.exit(1)

        self.ram[position] = binary_value

    def alu(self, op, reg_a, reg_b, immediate_value):
        """ALU operations."""

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        elif op == "SUB": 
            self.reg[reg_a] -= self.reg[reg_b]
        elif op == "MUL":
            self.reg[reg_a] *= self.reg[reg_b]
        elif op == "DIV":
            self.reg[reg_a] /= self.reg[reg_b]
        elif op == "MOD":
            if self.reg[reg_b] == 0:
                self.HLT()
                return

            self.reg[reg_a] %= self.reg[reg_b]
        elif op == "CMP":
            bit = 0b0

            if self.reg[reg_a] < self.reg[reg_b]:
                bit = 0b001
            elif self.reg[reg_a] > self.reg[reg_b]:
                bit = 0b010
            elif self.reg[reg_a] == self.reg[reg_b]:
                bit = 0b100

            self.reg[7] = bit
        elif op == "AND":
            self.reg[reg_a] = self.reg[reg_a] & self.reg[reg_b]
        elif op == "OR":
            self.reg[reg_a] = self.reg[reg_a] | self.reg[reg_b]
        elif op == "XOR":
            self.reg[reg_a] = self.reg[reg_a] ^ self.reg[reg_b]
        elif op == "NOT":
            self.reg[reg_a] = ~ self.reg[reg_a]
        elif op == "SHL":
            self.reg[reg_a] = self.reg[reg_a] << self.reg[reg_b]
        elif op == "SHR":
            self.reg[reg_a] = self.reg[reg_a] >> self.reg[reg_b]
        elif op == "ADDI":
            self.reg[reg_b] = self.reg[reg_a] + immediate_value
        else:
            raise Exception("Unsupported ALU operation")

    def push_stack(self, value):
        if self.ram_top - self.stack_last <= self.program_end + 1:
            raise Exception("Stack overflow")

        self.ram[self.ram_top - self.stack_last] = value
        self.stack_last += 1

        if self.DEBUG is True:
            print(f"PUSH: VAL: {value}")

            for i in range(self.stack_last):
                print(f"  {self.ram_top - i}: {self.ram[self.ram_top - i]}")

    def pop_stack(self, register = False):
        if self.stack_last == 0:
            raise Exception("Stack underflow")

        self.stack_last -= 1
        
        if self.DEBUG:
            print(f"POP: REG: {register}, ADDR: {self.ram_top - self.stack_last}, VAL: {self.ram[self.ram_top - self.stack_last]}")

        return_val = self.ram[self.ram_top - self.stack_last]
        self.ram[self.ram_top - self.stack_last] = 0b00000000

        return return_val

    def HLT(self):
        self.active = False

    def PRN(self):
        register = self.ram[self.instruction + 1]

        print(f"PRINT: LINE: {self.instruction}, REG: {register}, VAL: {self.reg[register]}")

        self.instruction += 2

    def INT(self):
        register = self.ram[self.instruction + 1]
        register_value = self.reg[register]

        self.reg[6] = register_value

        self.instruction += 2

    def IRET(self):
        r4 = self.pop_stack()
        r3 = self.pop_stack()
        r2 = self.pop_stack()
        r1 = self.pop_stack()
        r0 = self.pop_stack()

        FL = self.pop_stack()
        instruction = self.pop_stack()

        self.instruction = instruction

        self.disable_interrupts = False

    def LDI(self):
        register = self.ram[self.instruction + 1]
        value = self.ram[self.instruction + 2]

        if register < 0 or register >= len(self.reg):
            self.trace()
            print("SEG FAULT NO REG")
            sys.exit(1)

        if self.DEBUG:
            print(f"LOAD: LINE: {self.instruction}, REG: {register}, VAL: {value}")

        self.reg[register] = value

        self.instruction += 3

    def PUSH(self):
        register = self.ram[self.instruction + 1]

        self.push_stack(self.reg[register])

        self.instruction += 2

    def POP(self):
        register = self.ram[self.instruction + 1]

        self.reg[register] = self.pop_stack()

        self.instruction += 2

    def JMP(self):
        register = self.ram[self.instruction + 1]
        register_value = self.reg[register]

        self.instruction = register_value

    def JEQ(self):
        register = self.ram[self.instruction + 1]
        register_value = self.reg[register]

        equal_flag = self.reg[7] & 0b100

        if equal_flag == 0b100:
            self.instruction = register_value
        else:
            self.instruction += 2

    def JNE(self):
        register = self.ram[self.instruction + 1]
        register_value = self.reg[register]

        equal_flag = self.reg[7] & 0b100

        if equal_flag == 0:
            self.instruction = register_value
        else:
            self.instruction += 2

    def CALL(self):
        register = self.ram[self.instruction + 1]
        register_value = self.reg[register]

        if self.DEBUG:
            print("PUSH BY CALL")

        self.push_stack(self.instruction)

        if self.DEBUG:
            print(f"CALL: REG: {register}, VAL: {register_value}")

        self.instruction = register_value

    def RET(self):
        return_address = self.pop_stack()

        if self.DEBUG:
            print(f"RET: ADDR: {return_address}")

        self.instruction = return_address + 2

    def ALU_OP1(self):
        self.ALU_OP_JUMP(2)

    def ALU_OP2(self):
        self.ALU_OP_JUMP(3)

    def ALU_OP3(self):
        self.ALU_OP_JUMP(4)

    def ALU_OP_JUMP(self, skip_amount):
        op = self.ALU_OPS[self.ram[self.instruction]]
        register_a = self.ram[self.instruction + 1]
        register_b = self.ram[self.instruction + 2]
        immediate_value = self.ram[self.instruction + 3]

        self.alu(op, register_a, register_b, immediate_value)

        if self.DEBUG:
            print(f"{op.upper()}: LINE: {self.instruction}, REG_A: {register_a}, REG_B: {register_b}")

        self.instruction += skip_amount

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.instruction,
            #self.fl,
            #self.ie,
            self.ram_read(self.instruction),
            self.ram_read(self.instruction + 1),
            self.ram_read(self.instruction + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

    def check_interrupt(self, maskedInterrupts):
        for i in range(8):
            shift_1 = maskedInterrupts >> i

            if shift_1 & 0b1 == 0b1:
                self.reg[6] = 0b00000000

                self.push_stack(self.instruction)
                self.push_stack(self.reg[7])
                self.push_stack(self.reg[0])
                self.push_stack(self.reg[1])
                self.push_stack(self.reg[2])
                self.push_stack(self.reg[3])
                self.push_stack(self.reg[4])

                self.instruction = self.INTERRUPT_VECTORS[0b1 << i]
                self.disable_interrupts = True

                break

    def run(self, instruction_start = 0):
        """Run the CPU."""
        self.run_hot(instruction_start)

    def run_hot(self, instruction_start = 0):
        self.instruction = instruction_start
        self.active = True

        elapsed = time.time()

        while self.active:
            if time.time() - elapsed >= 1:
                self.reg[5] = 0b1

            if msvcrt.kbhit():
                key = msvcrt.getch()
                self.reg[5] = 0b10
                self.ram[0xF4] = key

            if self.disable_interrupts is False:
                self.check_interrupt(self.reg[5] & self.reg[6])

            instruction_val = self.ram[self.instruction]

            self.instruction_map[instruction_val]()

        print("HLT")
