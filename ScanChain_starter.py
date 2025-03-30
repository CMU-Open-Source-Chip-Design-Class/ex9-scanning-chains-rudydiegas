import random
import copy
import cocotb
from cocotb.triggers import Timer


# Make sure to set FILE_NAME
# to the filepath of the .log
# file you are working with
CHAIN_LENGTH = -1
FILE_NAME    = ""



# Holds information about a register
# in your design.

################
# DO NOT EDIT!!!
################
class Register:

    def __init__(self, name) -> None:
        self.name = name            # Name of register, as in .log file
        self.size = -1              # Number of bits in register

        self.bit_list = list()      # Set this to the register's contents, if you want to
        self.index_list = list()    # List of bit mappings into chain. See handout

        self.first = -1             # LSB mapping into scan chain
        self.last  = -1             # MSB mapping into scan chain


# Holds information about the scan chain
# in your design.

################
# DO NOT EDIT!!!
################
class ScanChain:

    def __init__(self) -> None:
        self.registers = dict()     # Dictionary of Register objects, indexed by
                                    # register name

        self.chain_length = 0       # Number of FFs in chain


# Sets up a new ScanChain object
# and returns it

################
# DO NOT EDIT!!!
################
def setup_chain(filename):

    scan_chain = ScanChain()

    f = open(filename, "r")
    for line in f:
        linelist = line.split()
        index, name, bit = linelist[0], linelist[1], linelist[2]

        if name not in scan_chain.registers:
            reg = Register(name)
            reg.index_list.append((int(bit), int(index)))
            scan_chain.registers[name] = reg

        else:
            scan_chain.registers[name].index_list.append((int(bit), int(index)))

    f.close()

    for name in scan_chain.registers:
        cur_reg = scan_chain.registers[name]
        cur_reg.index_list.sort()
        new_list = list()
        for tuple in cur_reg.index_list:
            new_list.append(tuple[1])

        cur_reg.index_list = new_list
        cur_reg.bit_list   = [0] * len(new_list)
        cur_reg.size = len(new_list)
        cur_reg.first = new_list[0]
        cur_reg.last  = new_list[-1]
        scan_chain.chain_length += len(cur_reg.index_list)

    return scan_chain


# Prints info of given Register object

################
# DO NOT EDIT!!!
################
def print_register(reg):
    print("------------------")
    print(f"NAME:    {reg.name}")
    print(f"BITS:    {reg.bit_list}")
    print(f"INDICES: {reg.index_list}")
    print("------------------")


# Prints info of given ScanChain object

################
# DO NOT EDIT!!!
################
def print_chain(chain):
    print("---CHAIN DISPLAY---\n")
    print(f"CHAIN SIZE: {chain.chain_length}\n")
    print("REGISTERS: \n")
    for name in chain.registers:
        cur_reg = chain.registers[name]
        print_register(cur_reg)



#-------------------------------------------------------------------

# This function steps the clock once.

# Hint: Use the Timer() builtin function
async def step_clock(dut):
    dut.clk.value = 1
    await Timer(10, units='ns')
    dut.clk.value = 0
    await Timer(10, units='ns')

#-------------------------------------------------------------------

# This function places a bit value inside FF of specified index.

# Hint: How many clocks would it take for value to reach
#       the specified FF?

async def input_chain_single(dut, bit, ff_index):
    wait_clks = ff_index
    dut.scan_in.value = bit
    dut.scan_en.value = 1
    await step_clock(dut)

    dut.scan_in.value = 0
    for i in range(wait_clks):
        await step_clock(dut)
    dut.scan_en.value = 0

#-------------------------------------------------------------------

# This function places multiple bit values inside FFs of specified indexes.
# This is an upgrade of input_chain_single() and should be accomplished
#   for Part H of Task 1

# Hint: How many clocks would it take for value to reach
#       the specified FF?

async def input_chain(dut, bit_list, ff_index):
    wait_clks = ff_index + len(bit_list)

    dut.scan_en.value = 1
    bit_index = ff_index + len(bit_list) - 1
    for i in range(wait_clks):
        if (bit_index >= 0):
            dut.scan_in.value = bit_list[bit_index]
            bit_index -= 1
        else:
            dut.scan_in.value = 0
        await step_clock(dut)

    dut.scan_en.value = 0

#-----------------------------------------------

# This function retrieves a single bit value from the
# chain at specified index

async def output_chain_single(dut, ff_index):
    wait_clks = CHAIN_LENGTH - (ff_index + 1)

    dut.scan_in.value = 0
    dut.scan_en.value = 1
    for i in range(wait_clks):
        await step_clock(dut)

    # pop it out
    ret_val = dut.scan_out.value
    await step_clock(dut)

    dut.scan_en.value = 0
    return ret_val

#-----------------------------------------------

# This function retrieves a single bit value from the
# chain at specified index
# This is an upgrade of input_chain_single() and should be accomplished
#   for Part H of Task 1

async def output_chain(dut, ff_index, output_length):
    last_idx = ff_index + output_length - 1
    clks_till_data = CHAIN_LENGTH - (last_idx + 1)
    wait_clks = CHAIN_LENGTH - (ff_index + 1)

    out = [0] * output_length

    bit_index = ff_index + output_length - 1
    dut.scan_in.value = 0
    dut.scan_en.value = 1
    for i in range(wait_clks):
        if (clks_till_data <= 0):
            out[bit_index] = dut.scan_out.value
            bit_index -= 1

        await step_clock(dut)
        clks_till_data -= 1

    # pop it out
    out[bit_index] = dut.scan_out.value
    await step_clock(dut)

    dut.scan_en.value = 0
    return out

#-----------------------------------------------

MIN_VAL = 0
MAX_VAL = 2**4 - 1

def gen_test_case():
  a_val = random.randint(MIN_VAL, MAX_VAL)
  b_val = random.randint(MIN_VAL, MAX_VAL)
  res = a_val + b_val

  a_bin = [0] * 4
  b_bin = [0] * 4

  for i in range(4):
      a_bin[i] = a_val & 1
      b_bin[i] = b_val & 1
      a_val = a_val >> 1
      b_val = b_val >> 1

  return (a_bin, b_bin, res)

# Your main testbench function

# @cocotb.test()
async def adder_test(dut):

    global CHAIN_LENGTH
    global FILE_NAME        # Make sure to edit this guy
                            # at the top of the file
    FILE_NAME = "adder/adder.log"

    # determinism
    random.seed(18224)

    # Setup the scan chain object
    chain = setup_chain(FILE_NAME)

    print_chain(chain)
    CHAIN_LENGTH = chain.chain_length

    zero_x = [0] * 5

    for i in range(20):
        a_val, b_val, res = gen_test_case()
        await input_chain(dut, (zero_x + a_val + b_val), 0)
        await step_clock(dut)

        print("TEST " + str(i) + ":")
        print("A: " + str(a_val))
        print("B: " + str(b_val))
        print("X: " + str(dut.x_out.value))
        print("CORRECT SUM:" + bin(res))
        print()

        assert dut.x_out.value == res

def get_bin_list(num, digits):
    num_bin = [0] * digits
    for i in range(digits):
        num_bin[i] = num & 1
        num = num >> 1

    return num_bin

# @cocotb.test()
async def hidden_test(dut):

    global CHAIN_LENGTH
    global FILE_NAME        # Make sure to edit this guy
                            # at the top of the file
    FILE_NAME = "hidden_fsm/hidden_fsm.log"

    # Setup the scan chain object
    chain = setup_chain(FILE_NAME)

    print_chain(chain)
    CHAIN_LENGTH = chain.chain_length

    for i in range(8):
        for j in range (2):
            bin_list = get_bin_list(i, 3)
            dut.data_avail.value = j
            await input_chain(dut, bin_list, 0)
            buf_en = dut.buf_en.value
            out_sel = dut.out_sel.value
            out_writing = dut.out_writing.value
            await step_clock(dut)
            next_state = (await output_chain(dut, 0, 3))

            # for formatting
            bin_list.reverse()
            next_state.reverse()
            print("data_avail: " + str(j))
            print("CURR_STATE: " + str(bin_list))
            print("NEXT_STATE: " + str(next_state))
            print("BUF_EN: " + str(buf_en))
            print("OUT_SEL: " + str(out_sel))
            print("OUT_WRITING: " + str(out_writing))
            print()

@cocotb.test()
async def fault_test(dut):
    faults = [(0b1111, [(0, "w0 SA0"),
                        (0, "w1 SA1"),
                        (0, "w2 SA0"),
                        (0, "w3 SA0")]),

              (0b1100, [(0, "w0 SA1"),
                        (0, "w1 SA0"),
                        (0, "w2 SA1")]),

              (0b1110, [(1, "w3 SA1")]),

              (0b0111, [(1, "w4 SA0"),
                        (1, "w5 SA1"),
                        (1, "w6 SA1"),
                        (1, "w7 SA1")]),

              (0b0011, [(0, "w4 SA1"),
                        (0, "w5 SA0")]),

              (0b1111, [(0, "w6 SA0"),
                        (0, "w7 SA0"),
                        (0, "w8 SA0")]),

              (0b0101, [(1, "w8 SA1")]),
             ]

    for (vec, pot_faults) in faults:
        dut.a.value = vec & 0x1
        dut.b.value = (vec & 0x2) >> 1
        dut.c.value = (vec & 0x4) >> 2
        dut.d.value = (vec & 0x8) >> 3
        await Timer(10, units='ns')

        out = dut.x.value
        print("VEC: " + bin(vec))
        print("X VAL: " + str(out))
        print("A VAL: " + str(dut.a.value))
        print("B VAL: " + str(dut.b.value))
        print("C VAL: " + str(dut.c.value))
        print("D VAL: " + str(dut.d.value))

        for (t, fault) in pot_faults:
            if (out == t):
                print("POSSIBLE " + fault)

        print()
