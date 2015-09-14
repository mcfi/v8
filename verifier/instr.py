#!/usr/bin/python
# This file contains all allowed instruction's binary encoding, which comes
# from Intel's software development document.

# Byte
def Byte(x):
    return '0x%02x' % x

def Imm8():
    return '0xXX'

def Imm16():
    return '%s %s' % (Imm8(), Imm8())

def Imm32():
    return '%s %s' % (Imm16(), Imm16())

def Imm64():
    return '%s %s' % (Imm32(), Imm32())

# Generate bits through bit-template x
def Bits(x):
    if x != '0' and x != '1':
        return '01'
    else:
        return x

# REX_low generation
def REX_low(template):
    assert(len(template) == 4);
    bits = [Bits(x) for x in template];
    assert(len(bits) == 4);
    for W in bits[0]:
        for R in bits[1]:
            for X in bits[2]:
                for B in bits[3]:
                    yield W+R+X+B

# REX generation
def REX(template):
    template = ''.join(template.strip().split())
    assert(len(template) == 8)
    high = template[:4]
    for low in REX_low(template[4:]):
        yield Byte(int(high + low, 2))

#for x in REX('0100 WR0B'):
#    print x

def Triplet(forbidden = set()):
    triplet = []
    bit = '01'
    for b0 in bit:
        for b1 in bit:
            for b2 in bit:
                b = b0 + b1 + b2
                if not b in forbidden:
                    yield b

#for x in Triplet(set(['000'])):
#    print x

# SIB not only enumerates sib bytes but also the immediates
def SIB(mod):
    assert(mod != '11')
    SS = ['00', '01', '10', '11']
    Index = [x for x in Triplet()]
    Base = [x for x in Triplet()]
    for ss in SS:
        for index in Index:
            for base in Base:
                sib = Byte(int(ss + index + base, 2))
                if mod == '00':
                    if base == '101':
                        yield '%s %s' % (sib, Imm32())
                    else:
                        yield sib
                elif mod == '01':
                    yield '%s %s' % (sib, Imm8())
                else:
                    yield '%s %s' % (sib, Imm32())

#for x in SIB('10'):
#    print x

def ModRM(template, forbidden_reg = set(), forbidden_rm = set()):
    template = template.strip().split()
    assert(len(template) == 3); # Mod Reg R/M
    Mod = None
    if template[0] == '11':
        Mod = ['11']
    else:
        Mod = ['00', '01', '10']
    Reg = None
    if template[1].isdigit():
        Reg = [template[1]]
    else:
        Reg = [x for x in Triplet(forbidden_reg)]
    RM = None
    if template[2].isdigit():
        RM = [template[2]]
    else:
        RM = [x for x in Triplet(forbidden_rm)]

    for mod in Mod:
        for reg in Reg:
            for rm in RM:
                modrm = Byte(int(mod + reg + rm, 2))
                if mod == '00':
                    if rm == '100':
                        for sib in SIB(mod):
                            yield '%s %s' % (modrm, sib)
                    elif rm == '101':
                        continue # RIP-relative addressing is not used in v8 JITted code
                    else:
                        yield modrm
                elif mod == '01':
                    if rm == '100':
                        for sib in SIB(mod):
                            yield '%s %s' % (modrm, sib)
                    else:
                        yield '%s %s' % (modrm, Imm8())
                elif mod == '10':
                    if rm == '100':
                        for sib in SIB(mod):
                            yield '%s %s' % (modrm, sib)
                    else:
                        yield '%s %s' % (modrm, Imm32())
                else: # mod == '11'
                    yield modrm

#for x in ModRM('mod reg r/m'):
#    print x

# Dictionary = []

class Encoding:
    def interpret_opcode(self, opcode):
        opcode = ''.join(opcode.strip().split())
        if len(opcode) == 8:
            return [opc for opc in REX(opcode)]
        if len(opcode) == 16:
            return [opc1 + ' ' + opc2 for opc1 in REX(opcode[:8]) for opc2 in REX(opcode[8:])]

    def __init__(self, prefix, rex, opcode, modrm = None,
                 forbidden_reg = set(), forbidden_rm = set(), \
                 imm_width = 0, extra = None, interpret_opcode = False):
        if prefix:
            self.prefix = [prefix]
        else:
            self.prefix = ['']

        if rex:
            self.rex = [rx for rx in REX(rex)]
        else:
            self.rex = ['']

        if not interpret_opcode:
            self.opcode = [opcode]
        else:
            self.opcode = self.interpret_opcode(opcode)

        if modrm:
            self.modrm = [mrm for mrm in ModRM(modrm, forbidden_reg, forbidden_rm)]
        else:
            self.modrm = ['']
        if imm_width == 8:
            self.imm_width = [Imm8()]
        elif imm_width == 16:
            self.imm_width = [Imm16()]
        elif imm_width == 32:
            self.imm_width = [Imm32()]
        elif imm_width == 64:
            self.imm_width = [Imm64()]
        else:
            self.imm_width = ['']

        if not extra:
            self.extra = ''
        else:
            self.extra = extra

    def encoding(self):
        for prx in self.prefix:
            for rex in self.rex:
                for opc in self.opcode:
                    for modrm in self.modrm:
                        for imm in self.imm_width:
                            yield '%s %s %s %s %s %s' % \
                                (prx, rex, opc, modrm, imm, self.extra)

    def init2(self, prefix, rex, opcode, forbidden_opcode = set(), imm_width = 0):
        if prefix:
            self.prefix = [prefix]
        else:
            self.prefix = ['']

        if rex:
            self.rex = [rx for rx in REX(rex)]
        else:
            self.rex = ['']

        if imm_width == 8:
            self.imm_width = [Imm8()]
        elif imm_width == 16:
            self.imm_width = [Imm16()]
        elif imm_width == 32:
            self.imm_width = [Imm32()]
        elif imm_width == 64:
            self.imm_width = [Imm64()]
        else:
            self.imm_width = ['']

        self.opcode = [opc for opc in REX(opcode) if not opc in forbidden_opcode ]
        #print self.opcode, forbidden_opcode
        return self

    def encoding2(self):
        for prx in self.prefix:
            for rex in self.rex:
                for opc in self.opcode:
                    for imm in self.imm_width:
                        yield '%s %s %s %s' % (prx, rex, opc, imm)

class Instruction:
    def __init__(self, name, attr = None):
        self.name = name
        if not attr:
            self.attr = ''
        else:
            self.attr = attr

    def dump(self, ecd):
        ecd = ' '.join([x[2:] for x in ecd.strip().split()]) + ':' + self.attr
        #ecd = ' '.join([x for x in ecd.strip().split()])
        print ecd

    def addform(self, prefix, rex, opcode, modrm = None, forbidden_reg = set(), \
                forbidden_rm = set(), imm_width = 0, extra = None, interpret_opcode = False):
        #global Dictionary
        for ecd in Encoding(prefix, rex, opcode, modrm, forbidden_reg, \
                            forbidden_rm, imm_width, extra, interpret_opcode).encoding():
            self.dump(ecd)
            #Dictionary += ecd

    def addform2(self, prefix, rex, opcode, forbidden_opcode = set(), imm_width = 0):
        #global Dictionary
        for ecd in Encoding(None, None, '').init2(prefix, rex, opcode, \
                                                  forbidden_opcode, imm_width).encoding2():
            self.dump(ecd)
            #Dictionary += ecd

SBX = '0x67'
OSIZE = '0x66'
SBXOSIZE = '0x67 0x66'

# Add instruction            
ADD = Instruction('add')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    ADD.addform(None, None, '0x00', '11 reg1 reg2')
    ADD.addform(None, None, '0x01', '11 reg1 reg2')
    ADD.addform(OSIZE, None, '0x01', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    ADD.addform(None, None, '0x02', '11 reg1 reg2')
    ADD.addform(None, None, '0x03', '11 reg1 reg2')
    ADD.addform(OSIZE, None, '0x03', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    ADD.addform(None, None, '0x02', 'mod reg r/m')
    ADD.addform(None, None, '0x03', 'mod reg r/m')
    ADD.addform(OSIZE, None, '0x03', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    ADD.addform(SBX, None, '0x00', 'mod reg r/m')
    ADD.addform(SBX, None, '0x01', 'mod reg r/m')
    ADD.addform(SBXOSIZE, None, '0x01', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    ADD.addform(None, None, '0x80', '11 000 reg', set(), set(), 8);
    ADD.addform(None, None, '0x81', '11 000 reg', set(), set(), 32);
    ADD.addform(OSIZE, None, '0x81', '11 000 reg', set(), set(), 16);
    ADD.addform(None, None, '0x83', '11 000 reg', set(), set(), 8);
    ADD.addform(OSIZE, None, '0x83', '11 000 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    ADD.addform(None, None, '0x04', None, set(), set(), 8)
    ADD.addform(None, None, '0x05', None, set(), set(), 32)
    ADD.addform(OSIZE, None, '0x05', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    ADD.addform(SBX, None, '0x80', 'mod 000 r/m', set(), set(), 8);
    ADD.addform(SBX, None, '0x81', 'mod 000 r/m', set(), set(), 32);
    ADD.addform(SBXOSIZE, None, '0x81', 'mod 000 r/m', set(), set(), 16);
    ADD.addform(SBX, None, '0x83', 'mod 000 r/m', set(), set(), 8);
    ADD.addform(SBXOSIZE, None, '0x83', 'mod 000 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    ADD.addform(None, '0100 0R0B', '0x00', '11 reg1 reg2')
    ADD.addform(None, '0100 0R0B', '0x01', '11 reg1 reg2')
    ADD.addform(OSIZE, '0100 0R0B', '0x01', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    ADD.addform(None, '0100 1R00', '0x01', '11 reg1 reg2', set(), set(['100']))
    ADD.addform(None, '0100 1R01', '0x01', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    ADD.addform(None, '0100 0R0B', '0x02', '11 reg1 reg2')
    ADD.addform(None, '0100 0R0B', '0x03', '11 reg1 reg2')
    ADD.addform(OSIZE, '0100 0R0B', '0x03', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    ADD.addform(None, '0100 100B', '0x03', '11 reg1 reg2', set(['100']), set())
    ADD.addform(None, '0100 110B', '0x03', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    ADD.addform(None, '0100 0RXB', '0x02', 'mod reg r/m')
    ADD.addform(None, '0100 0RXB', '0x03', 'mod reg r/m')
    ADD.addform(OSIZE, '0100 0RXB', '0x03', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    ADD.addform(None, '0100 10XB', '0x03', 'mod reg r/m', set(['100']))
    ADD.addform(None, '0100 11XB', '0x03', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    ADD.addform(SBX, '0100 0RXB', '0x00', 'mod reg r/m')
    ADD.addform(SBX, '0100 0RXB', '0x01', 'mod reg r/m')
    ADD.addform(SBXOSIZE, '0100 0RXB', '0x01', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0011 : mod qwordreg r/m
    ADD.addform(SBX, '0100 1RXB', '0x01', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    ADD.addform(None, '0100 000B', '0x80', '11 000 reg', set(), set(), 8);
    ADD.addform(None, '0100 000B', '0x81', '11 000 reg', set(), set(), 32)
    ADD.addform(OSIZE, '0100 000B', '0x81', '11 000 reg', set(), set(), 16)
    ADD.addform(None, '0100 000B', '0x83', '11 000 reg', set(), set(), 8)
    ADD.addform(OSIZE, '0100 000B', '0x83', '11 000 reg', set(), set(), 8)
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    ADD.addform(None, '0100 1000', '0x81', '11 000 reg', set(), set(['100']), 32)
    ADD.addform(None, '0100 1001', '0x81', '11 000 reg', set(), set(), 32)
    # immediate8 to qword register
    ADD.addform(None, '0100 1000', '0x83', '11 000 reg', set(), set(['100']), 8)
    ADD.addform(None, '0100 1001', '0x83', '11 000 reg', set(), set(), 8)
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    ADD.addform(None, '0100 1000', '0x05', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    ADD.addform(SBX, '0100 00XB', '0x80', 'mod 000 r/m', set(), set(), 8);
    ADD.addform(SBX, '0100 00XB', '0x81', 'mod 000 r/m', set(), set(), 32);
    ADD.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 000 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    ADD.addform(SBX, '0100 10XB', '0x81', 'mod 000 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0011 : mod 010 r/m : imm8
    ADD.addform(SBX, '0100 W0XB', '0x83', 'mod 000 r/m', set(), set(), 8)

# And instruction            
AND = Instruction('and')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    AND.addform(None, None, '0x20', '11 reg1 reg2')
    AND.addform(None, None, '0x21', '11 reg1 reg2')
    AND.addform(OSIZE, None, '0x21', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    AND.addform(None, None, '0x22', '11 reg1 reg2')
    AND.addform(None, None, '0x23', '11 reg1 reg2')
    AND.addform(OSIZE, None, '0x23', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    AND.addform(None, None, '0x22', 'mod reg r/m')
    AND.addform(None, None, '0x23', 'mod reg r/m')
    AND.addform(OSIZE, None, '0x23', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    AND.addform(SBX, None, '0x20', 'mod reg r/m')
    AND.addform(SBX, None, '0x21', 'mod reg r/m')
    AND.addform(SBXOSIZE, None, '0x21', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    AND.addform(None, None, '0x80', '11 100 reg', set(), set(), 8);
    AND.addform(None, None, '0x81', '11 100 reg', set(), set(), 32);
    AND.addform(OSIZE, None, '0x81', '11 100 reg', set(), set(), 16);
    AND.addform(None, None, '0x83', '11 100 reg', set(), set(), 8);
    AND.addform(OSIZE, None, '0x83', '11 100 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    AND.addform(None, None, '0x24', None, set(), set(), 8)
    AND.addform(None, None, '0x25', None, set(), set(), 32)
    AND.addform(OSIZE, None, '0x25', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    AND.addform(SBX, None, '0x80', 'mod 100 r/m', set(), set(), 8);
    AND.addform(SBX, None, '0x81', 'mod 100 r/m', set(), set(), 32);
    AND.addform(SBXOSIZE, None, '0x81', 'mod 100 r/m', set(), set(), 16);
    AND.addform(SBX, None, '0x80', 'mod 100 r/m', set(), set(), 8);
    AND.addform(SBXOSIZE, None, '0x80', 'mod 100 r/m', set(), set(), 8);
# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    AND.addform(None, '0100 0R0B', '0x20', '11 reg1 reg2')
    AND.addform(None, '0100 0R0B', '0x21', '11 reg1 reg2')
    AND.addform(OSIZE, '0100 0R0B', '0x21', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    AND.addform(None, '0100 1R00', '0x21', '11 reg1 reg2', set(), set(['100']))
    AND.addform(None, '0100 1R01', '0x21', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    AND.addform(None, '0100 0R0B', '0x22', '11 reg1 reg2')
    AND.addform(None, '0100 0R0B', '0x23', '11 reg1 reg2')
    AND.addform(OSIZE, '0100 0R0B', '0x23', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    AND.addform(None, '0100 100B', '0x23', '11 reg1 reg2', set(['100']), set())
    AND.addform(None, '0100 110B', '0x23', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    AND.addform(None, '0100 0RXB', '0x22', 'mod reg r/m')
    AND.addform(None, '0100 0RXB', '0x23', 'mod reg r/m')
    AND.addform(OSIZE, '0100 0RXB', '0x23', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    AND.addform(None, '0100 10XB', '0x23', 'mod reg r/m', set(['100']))
    AND.addform(None, '0100 11XB', '0x23', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    AND.addform(SBX, '0100 0RXB', '0x20', 'mod reg r/m')
    AND.addform(SBX, '0100 0RXB', '0x21', 'mod reg r/m')
    AND.addform(SBXOSIZE, '0100 0RXB', '0x21', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0011 : mod qwordreg r/m
    AND.addform(SBX, '0100 1RXB', '0x21', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    AND.addform(None, '0100 000B', '0x80', '11 100 reg', set(), set(), 8);
    AND.addform(None, '0100 000B', '0x81', '11 100 reg', set(), set(), 32);
    AND.addform(OSIZE, '0100 000B', '0x81', '11 100 reg', set(), set(), 16);
    AND.addform(None, '0100 000B', '0x83', '11 100 reg', set(), set(), 8);
    AND.addform(OSIZE, '0100 000B', '0x83', '11 100 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    AND.addform(None, '0100 1000', '0x81', '11 100 reg', set(), set(['100']), 32)
    AND.addform(None, '0100 1001', '0x81', '11 100 reg', set(), set(), 32)
    # immediate8 to qword reg
    AND.addform(None, '0100 100B', '0x83', '11 100 reg', set(), set(), 8);
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    AND.addform(None, '0100 1000', '0x25', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    AND.addform(SBX, '0100 00XB', '0x80', 'mod 100 r/m', set(), set(), 8);
    AND.addform(SBX, '0100 00XB', '0x81', 'mod 100 r/m', set(), set(), 32);
    AND.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 100 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    AND.addform(SBX, '0100 10XB', '0x81', 'mod 100 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0011 : mod 010 r/m : imm8
    AND.addform(SBX, '0100 W0XB', '0x83', 'mod 100 r/m', set(), set(), 8)

# Cmp instruction            
CMP = Instruction('cmp')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    CMP.addform(None, None, '0x38', '11 reg1 reg2')
    CMP.addform(None, None, '0x39', '11 reg1 reg2')
    CMP.addform(OSIZE, None, '0x39', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    CMP.addform(None, None, '0x3a', '11 reg1 reg2')
    CMP.addform(None, None, '0x3b', '11 reg1 reg2')
    CMP.addform(OSIZE, None, '0x3b', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    CMP.addform(None, None, '0x38', 'mod reg r/m')
    CMP.addform(None, None, '0x39', 'mod reg r/m')
    CMP.addform(OSIZE, None, '0x39', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    CMP.addform(None, None, '0x3a', 'mod reg r/m')
    CMP.addform(None, None, '0x3b', 'mod reg r/m')
    CMP.addform(OSIZE, None, '0x3b', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    CMP.addform(None, None, '0x80', '11 111 reg', set(), set(), 8);
    CMP.addform(None, None, '0x81', '11 111 reg', set(), set(), 32);
    CMP.addform(OSIZE, None, '0x81', '11 111 reg', set(), set(), 16);
    CMP.addform(None, None, '0x83', '11 111 reg', set(), set(), 8);
    CMP.addform(OSIZE, None, '0x83', '11 111 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    CMP.addform(None, None, '0x3c', None, set(), set(), 8)
    CMP.addform(None, None, '0x3d', None, set(), set(), 32)
    CMP.addform(OSIZE, None, '0x3d', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    CMP.addform(None, None, '0x80', 'mod 111 r/m', set(), set(), 8);
    CMP.addform(None, None, '0x81', 'mod 111 r/m', set(), set(), 32);
    CMP.addform(OSIZE, None, '0x81', 'mod 111 r/m', set(), set(), 16);
    CMP.addform(None, None, '0x83', 'mod 111 r/m', set(), set(), 8);
    CMP.addform(OSIZE, None, '0x83', 'mod 111 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    CMP.addform(None, '0100 0R0B', '0x38', '11 reg1 reg2')
    CMP.addform(None, '0100 0R0B', '0x39', '11 reg1 reg2')
    CMP.addform(OSIZE, '0100 0R0B', '0x39', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    CMP.addform(None, '0100 1R0B', '0x39', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    CMP.addform(None, '0100 0R0B', '0x3a', '11 reg1 reg2')
    CMP.addform(None, '0100 0R0B', '0x3b', '11 reg1 reg2')
    CMP.addform(OSIZE, '0100 0R0B', '0x3b', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    CMP.addform(None, '0100 1R0B', '0x3b', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    CMP.addform(None, '0100 0RXB', '0x38', 'mod reg r/m')
    CMP.addform(None, '0100 0RXB', '0x39', 'mod reg r/m')
    CMP.addform(OSIZE, '0100 0RXB', '0x39', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    CMP.addform(None, '0100 1RXB', '0x39', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    CMP.addform(None, '0100 0RXB', '0x3a', 'mod reg r/m')
    CMP.addform(None, '0100 0RXB', '0x3b', 'mod reg r/m')
    CMP.addform(OSIZE, '0100 0RXB', '0x3b', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0011 : mod qwordreg r/m
    CMP.addform(None, '0100 1RXB', '0x3b', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    CMP.addform(None, '0100 000B', '0x80', '11 111 reg', set(), set(), 8);
    CMP.addform(None, '0100 000B', '0x81', '11 111 reg', set(), set(), 32);
    CMP.addform(OSIZE, '0100 000B', '0x81', '11 111 reg', set(), set(), 16);
    CMP.addform(None, '0100 000B', '0x83', '11 111 reg', set(), set(), 8);
    CMP.addform(OSIZE, '0100 000B', '0x83', '11 111 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    CMP.addform(None, '0100 100B', '0x81', '11 111 reg', set(), set(), 32)
    CMP.addform(None, '0100 100B', '0x83', '11 111 reg', set(), set(), 8)
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    CMP.addform(None, '0100 1000', '0x3d', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    CMP.addform(None, '0100 00XB', '0x80', 'mod 111 r/m', set(), set(), 8);
    CMP.addform(None, '0100 00XB', '0x81', 'mod 111 r/m', set(), set(), 32);
    CMP.addform(OSIZE, '0100 00XB', '0x81', 'mod 111 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    CMP.addform(None, '0100 10XB', '0x81', 'mod 111 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0011 : mod 010 r/m : imm8
    CMP.addform(None, '0100 W0XB', '0x83', 'mod 111 r/m', set(), set(), 8)

# Dec instruction            
DEC = Instruction('dec')
# 32-bit
if True:
    # register 1111 111w : 11 001 reg
    DEC.addform(None, None, '0xfe', '11 001 reg')
    DEC.addform(None, None, '0xff', '11 001 reg')
    DEC.addform(OSIZE, None, '0xff', '11 001 reg')
    # register (alternate encoding) 0100 1 reg, N.E. in 64-bit
    # memory 1111 111w : mod 001 r/m
    DEC.addform(SBX, None, '0xfe', 'mod 001 r/m')
    DEC.addform(SBX, None, '0xff', 'mod 001 r/m')
    DEC.addform(SBXOSIZE, None, '0xff', 'mod 001 r/m')

if True:
    # register 0100 000B 1111 111w : 11 001 reg
    DEC.addform(None, '0100 000B', '0xfe', '11 001 reg')
    DEC.addform(None, '0100 000B', '0xff', '11 001 reg')
    DEC.addform(OSIZE, '0100 000B', '0xff', '11 001 reg')
    # qwordregister 0100 100B 1111 1111 : 11 001 qwordreg
    DEC.addform(None, '0100 1000', '0xff', '11 001 reg', set(), set(['100']))
    DEC.addform(None, '0100 1001', '0xff', '11 001 reg')
    # memory 0100 00XB 1111 111w : mod 001 r/m
    DEC.addform(SBX, '0100 00XB', '0xfe', 'mod 001 r/m')
    DEC.addform(SBX, '0100 00XB', '0xff', 'mod 001 r/m')
    DEC.addform(SBXOSIZE, '0100 00XB', '0xff', 'mod 001 r/m')
    # memory64 0100 10XB 1111 1111 : mod 001 r/m
    DEC.addform(SBX, '0100 10XB', '0xff', 'mod 001 r/m')

# Div instruction            
DIV = Instruction('div')
# 32-bit
if True:
    # AL, AX, or EAX by register 1111 011w : 11 110 reg
    DIV.addform(None, None, '0xf6', '11 110 reg')
    DIV.addform(None, None, '0xf7', '11 110 reg')
    DIV.addform(OSIZE, None, '0xf7', '11 110 reg')
    # AL, AX, or EAX by memory 1111 011w : mod 110 r/m
    DIV.addform(None, None, '0xf6', 'mod 110 r/m')
    DIV.addform(None, None, '0xf7', 'mod 110 r/m')
    DIV.addform(OSIZE, None, '0xf7', 'mod 110 r/m')

# 64-bit
if True:
    # AL, AX, or EAX by register 0100 000B 1111 011w : 11 110 reg
    DIV.addform(None, '0100 000B', '0xf6', '11 110 reg')
    DIV.addform(None, '0100 000B', '0xf7', '11 110 reg')
    DIV.addform(OSIZE, '0100 000B', '0xf7', '11 110 reg')
    # Divide RDX:RAX by qwordregister 0100 100B 1111 0111 : 11 110 qwordreg
    DIV.addform(None, '0100 100B', '0xf7', '11 110 reg')
    # AL, AX, or EAX by memory 0100 00XB 1111 011w : mod 110 r/m
    DIV.addform(None, '0100 00XB', '0xf6', 'mod 110 r/m')
    DIV.addform(None, '0100 00XB', '0xf7', 'mod 110 r/m')
    DIV.addform(OSIZE, '0100 00XB', '0xf7', 'mod 110 r/m')
    # Divide RDX:RAX by memory64 0100 10XB 1111 0111 : mod 110 r/m
    DIV.addform(None, '0100 10XB', '0xf7', 'mod 110 r/m')

# Mul instruction
MUL = Instruction('mul')
# 32-bit
if True:
    # AL, AX, or EAX by register 1111 011w : 11 110 reg
    MUL.addform(None, None, '0xf6', '11 100 reg')
    MUL.addform(None, None, '0xf7', '11 100 reg')
    MUL.addform(OSIZE, None, '0xf7', '11 100 reg')
    # AL, AX, or EAX by memory 1111 011w : mod 110 r/m
    MUL.addform(None, None, '0xf6', 'mod 100 r/m')
    MUL.addform(None, None, '0xf7', 'mod 100 r/m')
    MUL.addform(OSIZE, None, '0xf7', 'mod 100 r/m')

# 64-bit
if True:
    # AL, AX, or EAX by register 0100 000B 1111 011w : 11 100 reg
    MUL.addform(None, '0100 000B', '0xf6', '11 100 reg')
    MUL.addform(None, '0100 000B', '0xf7', '11 100 reg')
    MUL.addform(OSIZE, '0100 000B', '0xf7', '11 100 reg')
    # Divide RDX:RAX by qwordregister 0100 100B 1111 0111 : 11 100 qwordreg
    MUL.addform(None, '0100 100B', '0xf7', '11 100 reg')
    # AL, AX, or EAX by memory 0100 00XB 1111 011w : mod 100 r/m
    MUL.addform(None, '0100 00XB', '0xf6', 'mod 100 r/m')
    MUL.addform(None, '0100 00XB', '0xf7', 'mod 100 r/m')
    MUL.addform(OSIZE, '0100 00XB', '0xf7', 'mod 100 r/m')
    # Divide RDX:RAX by memory64 0100 10XB 1111 0111 : mod 100 r/m
    MUL.addform(None, '0100 10XB', '0xf7', 'mod 100 r/m')

# Idiv instruction
IDIV = Instruction('idiv')
# 32-bit
if True:
    # AL, AX, or EAX by register 1111 011w : 11 111 reg
    IDIV.addform(None, None, '0xf6', '11 111 reg')
    IDIV.addform(None, None, '0xf7', '11 111 reg')
    IDIV.addform(OSIZE, None, '0xf7', '11 111 reg')
    # AL, AX, or EAX by memory 1111 011w : mod 111 r/m
    IDIV.addform(None, None, '0xf6', 'mod 111 r/m')
    IDIV.addform(None, None, '0xf7', 'mod 111 r/m')
    IDIV.addform(OSIZE, None, '0xf7', 'mod 111 r/m')

# 64-bit
if True:
    # AL, AX, or EAX by register 0100 000B 1111 011w : 11 111 reg
    IDIV.addform(None, '0100 000B', '0xf6', '11 111 reg')
    IDIV.addform(None, '0100 000B', '0xf7', '11 111 reg')
    IDIV.addform(OSIZE, '0100 000B', '0xf7', '11 111 reg')
    # Divide RDX:RAX by qwordregister 0100 100B 1111 0111 : 11 111 qwordreg
    IDIV.addform(None, '0100 100B', '0xf7', '11 111 reg')
    # AL, AX, or EAX by memory 0100 00XB 1111 011w : mod 111 r/m
    IDIV.addform(None, '0100 00XB', '0xf6', 'mod 111 r/m')
    IDIV.addform(None, '0100 00XB', '0xf7', 'mod 111 r/m')
    IDIV.addform(OSIZE, '0100 00XB', '0xf7', 'mod 111 r/m')
    # Divide RDX:RAX by memory64 0100 10XB 1111 0111 : mod 111 r/m
    IDIV.addform(None, '0100 10XB', '0xf7', 'mod 111 r/m')

# Imul instruction
IMUL = Instruction('imul')
# 32-bit
if True:
    # AL, AX, or EAX with register 1111 011w : 11 101 reg
    IMUL.addform(None, None, '0xf6', '11 101 reg')
    IMUL.addform(None, None, '0xf7', '11 101 reg')
    IMUL.addform(OSIZE, None, '0xf7', '11 101 reg')
    # AL, AX, or EAX with memory 1111 011w : mod 101 r/m
    IMUL.addform(None, None, '0xf6', 'mod 101 r/m')
    IMUL.addform(None, None, '0xf7', 'mod 101 r/m')
    IMUL.addform(OSIZE, None, '0xf7', 'mod 101 r/m')
    # register1 with register2 0000 1111 : 1010 1111 : 11 reg1 reg2
    IMUL.addform(None, None, '0x0f 0xaf', '11 reg1 reg2')
    IMUL.addform(OSIZE, None, '0x0f 0xaf', '11 reg1 reg2')
    # register with memory 0000 1111 : 1010 1111 : mod reg r/m
    IMUL.addform(None, None, '0x0f 0xaf', 'mod reg r/m')
    IMUL.addform(OSIZE, None, '0x0f 0xaf', 'mod reg r/m')
    # register1 with immediate to register2 0110 10s1 : 11 reg1 reg2 : immediate data
    IMUL.addform(None, None, '0x6b', '11 reg1 reg2', set(), set(), 8)
    IMUL.addform(OSIZE, None, '0x6b', '11 reg1 reg2', set(), set(), 8)
    IMUL.addform(None, None, '0x69', '11 reg1 reg2', set(), set(), 32)
    IMUL.addform(OSIZE, None, '0x69', '11 reg1 reg2', set(), set(), 16)
    # memory with immediate to register 0110 10s1 : mod reg r/m : immediate data
    IMUL.addform(None, None, '0x6b', 'mod reg r/m', set(), set(), 8)
    IMUL.addform(OSIZE, None, '0x6b', 'mod reg r/m', set(), set(), 8)
    IMUL.addform(None, None, '0x69', 'mod reg r/m', set(), set(), 32)
    IMUL.addform(OSIZE, None, '0x69', 'mod reg r/m', set(), set(), 16)

# 64-bit
if True:
    # AL, AX, or EAX by register 0100 000B 1011 011w : 11 101 reg
    IMUL.addform(None, '0100 000B', '0xf6', '11 101 reg')
    IMUL.addform(None, '0100 000B', '0xf7', '11 101 reg')
    IMUL.addform(OSIZE, '0100 000B', '0xf7', '11 101 reg')
    # RDX:RAX <- RAX with qwordregister 0100 100B 1111 0111 : 11 101 qwordreg
    IMUL.addform(None, '0100 100B', '0xf7', '11 101 reg')
    # AL, AX, or EAX by memory 0100 00XB 1011 011w : mod 101 r/m
    IMUL.addform(None, '0100 00XB', '0xf6', 'mod 101 r/m')
    IMUL.addform(None, '0100 00XB', '0xf7', 'mod 101 r/m')
    IMUL.addform(OSIZE, '0100 00XB', '0xf7', 'mod 101 r/m')
    # RDX:RAX <- RAX with memory64 0100 10XB 1111 0111 : mod 101 r/m
    IMUL.addform(None, '0100 10XB', '0xf7', 'mod 101 r/m')
    # register1 with register2 0000 1111 : 1010 1111 : 11 reg1 reg2
    IMUL.addform(None, '0100 0R0B', '0x0f 0xaf', '11 reg1 reg2')
    IMUL.addform(OSIZE, '0100 0R0B', '0x0f 0xaf', '11 reg1 reg2')
    # qwordregister1 <- qwordregister1 with qwordregister2
    # 0100 1R0B 0000 1111 : 1010 1111 : 11 : qwordreg1 qwordreg2
    IMUL.addform(None, '0100 1R0B', '0x0f 0xaf', '11 reg1 reg2')
    # register with memory 0100 0RXB 0000 1111 : 1010 1111 : mod reg r/m
    IMUL.addform(None, '0100 WRXB', '0x0f 0xaf', 'mod reg r/m')
    IMUL.addform(OSIZE, '0100 0RXB', '0x0f 0xaf', 'mod reg r/m')
    # register1 with immediate to register2 0110 10s1 : 11 reg1 reg2 : immediate data
    IMUL.addform(None, '0100 0R0B', '0x6b', '11 reg1 reg2', set(), set(), 8)
    IMUL.addform(OSIZE, '0100 0R0B', '0x6b', '11 reg1 reg2', set(), set(), 8)
    IMUL.addform(None, '0100 0R0B', '0x69', '11 reg1 reg2', set(), set(), 32)
    IMUL.addform(OSIZE, '0100 0R0B', '0x69', '11 reg1 reg2', set(), set(), 16)
    # qwordregister1 <- qwordregister2 with sign-extended immediate8
    # 0100 1R0B 0110 1011 : 11 qwordreg1 qwordreg2 : imm8
    IMUL.addform(None, '0100 1R0B', '0x6b', '11 reg1 reg2', set(), set(), 8)
    # qwordregister1 <- qwordregister2 with immediate32
    # 0100 1R0B 0110 1001 : 11 qwordreg1 qwordreg2 : imm32
    IMUL.addform(None, '0100 1R0B', '0x69', '11 reg1 reg2', set(), set(), 32)
    # memory with immediate to register 0110 10s1 : mod reg r/m : immediate data
    IMUL.addform(None, '0100 0RXB', '0x6b', 'mod reg r/m', set(), set(), 8)
    IMUL.addform(OSIZE, '0100 0RXB', '0x6b', 'mod reg r/m', set(), set(), 8)
    IMUL.addform(None, '0100 0RXB', '0x69', 'mod reg r/m', set(), set(), 32)
    IMUL.addform(OSIZE, '0100 0RXB', '0x69', 'mod reg r/m', set(), set(), 16)
    # qwordregister <- memory64 with sign-extended immediate8
    # 0100 1RXB 0110 1011 : mod qwordreg r/m : imm8
    IMUL.addform(None, '0100 1RXB', '0x6b', 'mod reg r/m', set(), set(), 8)
    # qwordregister <- memory64 with immediate32
    # 0100 1RXB 0110 1001 : mod qwordreg r/m : imm32
    IMUL.addform(None, '0100 1RXB', '0x69', 'mod reg r/m', set(), set(), 32)

# Inc instruction            
INC = Instruction('inc')
# 32-bit
if True:
    # register 1111 111w : 11 000 reg
    INC.addform(None, None, '0xfe', '11 000 reg')
    INC.addform(None, None, '0xff', '11 000 reg')
    INC.addform(OSIZE, None, '0xff', '11 000 reg')
    # register (alternate encoding) 0100 0 reg, N.E. in 64-bit
    # memory 1111 111w : mod 000 r/m
    INC.addform(SBX, None, '0xfe', 'mod 000 r/m')
    INC.addform(SBX, None, '0xff', 'mod 000 r/m')
    INC.addform(SBXOSIZE, None, '0xff', 'mod 000 r/m')

if True:
    # register 0100 000B 1111 111w : 11 000 reg
    INC.addform(None, '0100 000B', '0xfe', '11 000 reg')
    INC.addform(None, '0100 000B', '0xff', '11 000 reg')
    INC.addform(OSIZE, '0100 000B', '0xff', '11 000 reg')
    # qwordregister 0100 100B 1111 1111 : 11 000 qwordreg
    INC.addform(None, '0100 1000', '0xff', '11 000 reg', set(), set(['100']))
    INC.addform(None, '0100 1001', '0xff', '11 000 reg')
    # memory 0100 00XB 1111 111w : mod 000 r/m
    INC.addform(SBX, '0100 00XB', '0xfe', 'mod 000 r/m')
    INC.addform(SBX, '0100 00XB', '0xff', 'mod 000 r/m')
    INC.addform(SBXOSIZE, '0100 00XB', '0xff', 'mod 000 r/m')
    # memory64 0100 10XB 1111 1111 : mod 000 r/m
    INC.addform(SBX, '0100 10XB', '0xff', 'mod 000 r/m')

# Neg instruction            
NEG = Instruction('neg')
# 32-bit
if True:
    # register 1111 111w : 11 011 reg
    NEG.addform(None, None, '0xf6', '11 011 reg')
    NEG.addform(None, None, '0xf7', '11 011 reg')
    NEG.addform(OSIZE, None, '0xf7', '11 011 reg')
    # register (alternate encoding) 0100 0 reg, N.E. in 64-bit
    # memory 1111 111w : mod 011 r/m
    NEG.addform(SBX, None, '0xf6', 'mod 011 r/m')
    NEG.addform(SBX, None, '0xf7', 'mod 011 r/m')
    NEG.addform(SBXOSIZE, None, '0xf7', 'mod 011 r/m')

if True:
    # register 0100 000B 1111 111w : 11 011 reg
    NEG.addform(None, '0100 000B', '0xf6', '11 011 reg')
    NEG.addform(None, '0100 000B', '0xf7', '11 011 reg')
    NEG.addform(OSIZE, '0100 000B', '0xf7', '11 011 reg')
    # qwordregister 0100 100B 1111 1111 : 11 011 qwordreg
    NEG.addform(None, '0100 1000', '0xf7', '11 011 reg', set(), set(['100']))
    NEG.addform(None, '0100 1001', '0xf7', '11 011 reg')
    # memory 0100 00XB 1111 111w : mod 011 r/m
    NEG.addform(SBX, '0100 00XB', '0xf6', 'mod 011 r/m')
    NEG.addform(SBX, '0100 00XB', '0xf7', 'mod 011 r/m')
    NEG.addform(SBXOSIZE, '0100 00XB', '0xf7', 'mod 011 r/m')
    # memory64 0100 10XB 1111 1111 : mod 011 r/m
    NEG.addform(SBX, '0100 10XB', '0xf7', 'mod 011 r/m')

# Not instruction            
NOT = Instruction('not')
# 32-bit
if True:
    # register 1111 111w : 11 010 reg
    NOT.addform(None, None, '0xf6', '11 010 reg')
    NOT.addform(None, None, '0xf7', '11 010 reg')
    NOT.addform(OSIZE, None, '0xf7', '11 010 reg')
    # register (alternate encoding) 0100 0 reg, N.E. in 64-bit
    # memory 1111 111w : mod 010 r/m
    NOT.addform(SBX, None, '0xf6', 'mod 010 r/m')
    NOT.addform(SBX, None, '0xf7', 'mod 010 r/m')
    NOT.addform(SBXOSIZE, None, '0xf7', 'mod 010 r/m')

if True:
    # register 0100 000B 1111 111w : 11 010 reg
    NOT.addform(None, '0100 000B', '0xf6', '11 010 reg')
    NOT.addform(None, '0100 000B', '0xf7', '11 010 reg')
    NOT.addform(OSIZE, '0100 000B', '0xf7', '11 010 reg')
    # qwordregister 0100 100B 1111 1111 : 11 010 qwordreg
    NOT.addform(None, '0100 1000', '0xf7', '11 010 reg', set(), set(['100']))
    NOT.addform(None, '0100 1001', '0xf7', '11 010 reg')
    # memory 0100 00XB 1111 111w : mod 010 r/m
    NOT.addform(SBX, '0100 00XB', '0xf6', 'mod 010 r/m')
    NOT.addform(SBX, '0100 00XB', '0xf7', 'mod 010 r/m')
    NOT.addform(SBXOSIZE, '0100 00XB', '0xf7', 'mod 010 r/m')
    # memory64 0100 10XB 1111 1111 : mod 010 r/m
    NOT.addform(SBX, '0100 10XB', '0xf7', 'mod 010 r/m')

# Or instruction            
OR = Instruction('or')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    OR.addform(None, None, '0x08', '11 reg1 reg2')
    OR.addform(None, None, '0x09', '11 reg1 reg2')
    OR.addform(OSIZE, None, '0x09', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    OR.addform(None, None, '0x0a', '11 reg1 reg2')
    OR.addform(None, None, '0x0b', '11 reg1 reg2')
    OR.addform(OSIZE, None, '0x0b', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    OR.addform(None, None, '0x0a', 'mod reg r/m')
    OR.addform(None, None, '0x0b', 'mod reg r/m')
    OR.addform(OSIZE, None, '0x0b', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    OR.addform(SBX, None, '0x08', 'mod reg r/m')
    OR.addform(SBX, None, '0x09', 'mod reg r/m')
    OR.addform(SBXOSIZE, None, '0x09', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    OR.addform(None, None, '0x80', '11 001 reg', set(), set(), 8);
    OR.addform(None, None, '0x81', '11 001 reg', set(), set(), 32);
    OR.addform(OSIZE, None, '0x81', '11 001 reg', set(), set(), 16);
    OR.addform(None, None, '0x83', '11 001 reg', set(), set(), 8);
    OR.addform(OSIZE, None, '0x83', '11 001 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    OR.addform(None, None, '0x0c', None, set(), set(), 8)
    OR.addform(None, None, '0x0d', None, set(), set(), 32)
    OR.addform(OSIZE, None, '0x0d', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    OR.addform(SBX, None, '0x80', 'mod 001 r/m', set(), set(), 8);
    OR.addform(SBX, None, '0x81', 'mod 001 r/m', set(), set(), 32);
    OR.addform(SBXOSIZE, None, '0x81', 'mod 001 r/m', set(), set(), 16);
    OR.addform(SBX, None, '0x83', 'mod 001 r/m', set(), set(), 8);
    OR.addform(SBXOSIZE, None, '0x83', 'mod 001 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    OR.addform(None, '0100 0R0B', '0x08', '11 reg1 reg2')
    OR.addform(None, '0100 0R0B', '0x09', '11 reg1 reg2')
    OR.addform(OSIZE, '0100 0R0B', '0x09', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    OR.addform(None, '0100 1R00', '0x09', '11 reg1 reg2', set(), set(['100']))
    OR.addform(None, '0100 1R01', '0x09', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    OR.addform(None, '0100 0R0B', '0x0a', '11 reg1 reg2')
    OR.addform(None, '0100 0R0B', '0x0b', '11 reg1 reg2')
    OR.addform(OSIZE, '0100 0R0B', '0x0b', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    OR.addform(None, '0100 100B', '0x0b', '11 reg1 reg2', set(['100']), set())
    OR.addform(None, '0100 110B', '0x0b', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    OR.addform(None, '0100 0RXB', '0x0a', 'mod reg r/m')
    OR.addform(None, '0100 0RXB', '0x0b', 'mod reg r/m')
    OR.addform(OSIZE, '0100 0RXB', '0x0b', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    OR.addform(None, '0100 10XB', '0x0b', 'mod reg r/m', set(['100']))
    OR.addform(None, '0100 11XB', '0x0b', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    OR.addform(SBX, '0100 0RXB', '0x08', 'mod reg r/m')
    OR.addform(SBX, '0100 0RXB', '0x09', 'mod reg r/m')
    OR.addform(SBXOSIZE, '0100 0RXB', '0x09', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0011 : mod qwordreg r/m
    OR.addform(SBX, '0100 1RXB', '0x09', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    OR.addform(None, '0100 000B', '0x80', '11 001 reg', set(), set(), 8);
    OR.addform(None, '0100 000B', '0x81', '11 001 reg', set(), set(), 32);
    OR.addform(OSIZE, '0100 000B', '0x81', '11 001 reg', set(), set(), 16);
    OR.addform(None, '0100 000B', '0x83', '11 001 reg', set(), set(), 8);
    OR.addform(OSIZE, '0100 000B', '0x83', '11 001 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    OR.addform(None, '0100 1000', '0x81', '11 001 reg', set(), set(['100']), 32)
    OR.addform(None, '0100 1001', '0x81', '11 001 reg', set(), set(), 32)
    # imm8 to qreg
    OR.addform(None, '0100 100B', '0x83', '11 001 reg', set(), set(), 8);
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    OR.addform(None, '0100 1000', '0x0d', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    OR.addform(SBX, '0100 00XB', '0x80', 'mod 001 r/m', set(), set(), 8);
    OR.addform(SBX, '0100 00XB', '0x81', 'mod 001 r/m', set(), set(), 32);
    OR.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 001 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    OR.addform(SBX, '0100 10XB', '0x81', 'mod 001 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0011 : mod 010 r/m : imm8
    OR.addform(SBX, '0100 W0XB', '0x83', 'mod 001 r/m', set(), set(), 8)

# Sbb instruction            
SBB = Instruction('sbb')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    SBB.addform(None, None, '0x18', '11 reg1 reg2')
    SBB.addform(None, None, '0x19', '11 reg1 reg2')
    SBB.addform(OSIZE, None, '0x19', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    SBB.addform(None, None, '0x1a', '11 reg1 reg2')
    SBB.addform(None, None, '0x1b', '11 reg1 reg2')
    SBB.addform(OSIZE, None, '0x1b', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    SBB.addform(None, None, '0x1a', 'mod reg r/m')
    SBB.addform(None, None, '0x1b', 'mod reg r/m')
    SBB.addform(OSIZE, None, '0x1b', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    SBB.addform(SBX, None, '0x18', 'mod reg r/m')
    SBB.addform(SBX, None, '0x19', 'mod reg r/m')
    SBB.addform(SBXOSIZE, None, '0x19', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    SBB.addform(None, None, '0x80', '11 011 reg', set(), set(), 8);
    SBB.addform(None, None, '0x81', '11 011 reg', set(), set(), 32);
    SBB.addform(OSIZE, None, '0x81', '11 011 reg', set(), set(), 16);
    SBB.addform(None, None, '0x83', '11 011 reg', set(), set(), 8);
    SBB.addform(OSIZE, None, '0x83', '11 011 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    SBB.addform(None, None, '0x1c', None, set(), set(), 8)
    SBB.addform(None, None, '0x1d', None, set(), set(), 32)
    SBB.addform(OSIZE, None, '0x1d', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    SBB.addform(SBX, None, '0x80', 'mod 011 r/m', set(), set(), 8);
    SBB.addform(SBX, None, '0x81', 'mod 011 r/m', set(), set(), 32);
    SBB.addform(SBXOSIZE, None, '0x81', 'mod 011 r/m', set(), set(), 16);
    SBB.addform(SBX, None, '0x83', 'mod 011 r/m', set(), set(), 8);
    SBB.addform(SBXOSIZE, None, '0x83', 'mod 011 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    SBB.addform(None, '0100 0R0B', '0x18', '11 reg1 reg2')
    SBB.addform(None, '0100 0R0B', '0x19', '11 reg1 reg2')
    SBB.addform(OSIZE, '0100 0R0B', '0x19', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    SBB.addform(None, '0100 1R00', '0x19', '11 reg1 reg2', set(), set(['100']))
    SBB.addform(None, '0100 1R01', '0x19', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    SBB.addform(None, '0100 0R0B', '0x1a', '11 reg1 reg2')
    SBB.addform(None, '0100 0R0B', '0x1b', '11 reg1 reg2')
    SBB.addform(OSIZE, '0100 0R0B', '0x1b', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    SBB.addform(None, '0100 100B', '0x1b', '11 reg1 reg2', set(['100']), set())
    SBB.addform(None, '0100 110B', '0x1b', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    SBB.addform(None, '0100 0RXB', '0x1a', 'mod reg r/m')
    SBB.addform(None, '0100 0RXB', '0x1b', 'mod reg r/m')
    SBB.addform(OSIZE, '0100 0RXB', '0x1b', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    SBB.addform(None, '0100 10XB', '0x1b', 'mod reg r/m', set(['100']))
    SBB.addform(None, '0100 11XB', '0x1b', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    SBB.addform(SBX, '0100 0RXB', '0x18', 'mod reg r/m')
    SBB.addform(SBX, '0100 0RXB', '0x19', 'mod reg r/m')
    SBB.addform(SBXOSIZE, '0100 0RXB', '0x19', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0011 : mod qwordreg r/m
    SBB.addform(SBX, '0100 1RXB', '0x19', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    SBB.addform(None, '0100 000B', '0x80', '11 011 reg', set(), set(), 8);
    SBB.addform(None, '0100 000B', '0x81', '11 011 reg', set(), set(), 32);
    SBB.addform(OSIZE, '0100 000B', '0x81', '11 011 reg', set(), set(), 16);
    SBB.addform(None, '0100 000B', '0x83', '11 011 reg', set(), set(), 8);
    SBB.addform(OSIZE, '0100 000B', '0x83', '11 011 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    SBB.addform(None, '0100 1000', '0x81', '11 011 reg', set(), set(['100']), 32)
    SBB.addform(None, '0100 1001', '0x81', '11 011 reg', set(), set(), 32)
    # immediate8 to qwordregister
    SBB.addform(None, '0100 1000', '0x83', '11 011 reg', set(), set(['100']), 8);
    SBB.addform(None, '0100 1001', '0x83', '11 011 reg', set(), set(), 8);
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    SBB.addform(None, '0100 1000', '0x1d', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    SBB.addform(SBX, '0100 00XB', '0x80', 'mod 011 r/m', set(), set(), 8);
    SBB.addform(SBX, '0100 00XB', '0x81', 'mod 011 r/m', set(), set(), 32);
    SBB.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 011 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    SBB.addform(SBX, '0100 10XB', '0x81', 'mod 011 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0011 : mod 010 r/m : imm8
    SBB.addform(SBX, '0100 W0XB', '0x83', 'mod 011 r/m', set(), set(), 8)

# Sub instruction            
SUB = Instruction('sub')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    SUB.addform(None, None, '0x28', '11 reg1 reg2')
    SUB.addform(None, None, '0x29', '11 reg1 reg2')
    SUB.addform(OSIZE, None, '0x29', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    SUB.addform(None, None, '0x2a', '11 reg1 reg2')
    SUB.addform(None, None, '0x2b', '11 reg1 reg2')
    SUB.addform(OSIZE, None, '0x2b', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    SUB.addform(None, None, '0x2a', 'mod reg r/m')
    SUB.addform(None, None, '0x2b', 'mod reg r/m')
    SUB.addform(OSIZE, None, '0x2b', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    SUB.addform(SBX, None, '0x28', 'mod reg r/m')
    SUB.addform(SBX, None, '0x29', 'mod reg r/m')
    SUB.addform(SBXOSIZE, None, '0x29', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    SUB.addform(None, None, '0x80', '11 101 reg', set(), set(), 8);
    SUB.addform(None, None, '0x81', '11 101 reg', set(), set(), 32);
    SUB.addform(OSIZE, None, '0x81', '11 101 reg', set(), set(), 16);
    SUB.addform(None, None, '0x83', '11 101 reg', set(), set(), 8);
    SUB.addform(OSIZE, None, '0x83', '11 101 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    SUB.addform(None, None, '0x2c', None, set(), set(), 8)
    SUB.addform(None, None, '0x2d', None, set(), set(), 32)
    SUB.addform(OSIZE, None, '0x2d', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    SUB.addform(SBX, None, '0x80', 'mod 101 r/m', set(), set(), 8);
    SUB.addform(SBX, None, '0x81', 'mod 101 r/m', set(), set(), 32);
    SUB.addform(SBXOSIZE, None, '0x81', 'mod 101 r/m', set(), set(), 16);
    SUB.addform(SBX, None, '0x83', 'mod 101 r/m', set(), set(), 8);
    SUB.addform(SBXOSIZE, None, '0x83', 'mod 101 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    SUB.addform(None, '0100 0R0B', '0x28', '11 reg1 reg2')
    SUB.addform(None, '0100 0R0B', '0x29', '11 reg1 reg2')
    SUB.addform(OSIZE, '0100 0R0B', '0x29', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    SUB.addform(None, '0100 1R00', '0x29', '11 reg1 reg2', set(), set(['100']))
    SUB.addform(None, '0100 1R01', '0x29', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    SUB.addform(None, '0100 0R0B', '0x2a', '11 reg1 reg2')
    SUB.addform(None, '0100 0R0B', '0x2b', '11 reg1 reg2')
    SUB.addform(OSIZE, '0100 0R0B', '0x2b', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    SUB.addform(None, '0100 100B', '0x2b', '11 reg1 reg2', set(['100']), set())
    SUB.addform(None, '0100 110B', '0x2b', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    SUB.addform(None, '0100 0RXB', '0x2a', 'mod reg r/m')
    SUB.addform(None, '0100 0RXB', '0x2b', 'mod reg r/m')
    SUB.addform(OSIZE, '0100 0RXB', '0x2b', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    SUB.addform(None, '0100 10XB', '0x2b', 'mod reg r/m', set(['100']))
    SUB.addform(None, '0100 11XB', '0x2b', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    SUB.addform(SBX, '0100 0RXB', '0x28', 'mod reg r/m')
    SUB.addform(SBX, '0100 0RXB', '0x29', 'mod reg r/m')
    SUB.addform(SBXOSIZE, '0100 0RXB', '0x29', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0101 : mod qwordreg r/m
    SUB.addform(SBX, '0100 1RXB', '0x29', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    SUB.addform(None, '0100 000B', '0x80', '11 101 reg', set(), set(), 8);
    SUB.addform(None, '0100 000B', '0x81', '11 101 reg', set(), set(), 32);
    SUB.addform(OSIZE, '0100 000B', '0x81', '11 101 reg', set(), set(), 16);
    SUB.addform(None, '0100 000B', '0x83', '11 101 reg', set(), set(), 8);
    SUB.addform(OSIZE, '0100 000B', '0x83', '11 101 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    SUB.addform(None, '0100 1000', '0x81', '11 101 reg', set(), set(['100']), 32)
    SUB.addform(None, '0100 1001', '0x81', '11 101 reg', set(), set(), 32)
    # immediate8 to qword reg
    SUB.addform(None, '0100 1000', '0x83', '11 101 reg', set(), set(['100']), 8);
    SUB.addform(None, '0100 1001', '0x83', '11 101 reg', set(), set(), 8);
    # immediate to RAX 0100 1000 : 0000 0101 : imm32
    SUB.addform(None, '0100 1000', '0x2d', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    SUB.addform(SBX, '0100 00XB', '0x80', 'mod 101 r/m', set(), set(), 8);
    SUB.addform(SBX, '0100 00XB', '0x81', 'mod 101 r/m', set(), set(), 32);
    SUB.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 101 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    SUB.addform(SBX, '0100 10XB', '0x81', 'mod 101 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0101 : mod 010 r/m : imm8
    SUB.addform(SBX, '0100 W0XB', '0x83', 'mod 101 r/m', set(), set(), 8)

# Rotate
ROTATE = Instruction('rotate')
# 32-bit
if True:
    # RCL
    ROTATE.addform(None, None, '0xd1', '11 010 reg')
    ROTATE.addform(None, None, '0xc1', '11 010 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, None, '0xd1', '11 010 reg')
    ROTATE.addform(None, None, '0xd3', '11 010 reg')
    # RCR
    ROTATE.addform(None, None, '0xd1', '11 011 reg')
    ROTATE.addform(None, None, '0xc1', '11 011 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, None, '0xd1', '11 011 reg')
    ROTATE.addform(None, None, '0xd3', '11 011 reg')
    # ROL
    ROTATE.addform(None, None, '0xd1', '11 000 reg')
    ROTATE.addform(None, None, '0xc1', '11 000 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, None, '0xd1', '11 000 reg')
    ROTATE.addform(None, None, '0xd3', '11 000 reg')
    # ROR
    ROTATE.addform(None, None, '0xd1', '11 001 reg')
    ROTATE.addform(None, None, '0xc1', '11 001 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, None, '0xd1', '11 001 reg')
    ROTATE.addform(None, None, '0xd3', '11 001 reg')

if True:
    # RCL
    ROTATE.addform(None, '0100 0RXB', '0xd1', '11 010 reg')
    ROTATE.addform(None, '0100 0RXB', '0xc1', '11 010 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, '0100 0RXB', '0xd1', '11 010 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd1', '11 010 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd1', '11 010 reg')
    ROTATE.addform(None, '0100 1RX0', '0xc1', '11 010 reg', set(), set(['100']), 8)
    ROTATE.addform(None, '0100 1RX1', '0xc1', '11 010 reg', set(), set(), 8)
    ROTATE.addform(None, '0100 0RXB', '0xd3', '11 010 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd3', '11 010 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd3', '11 010 reg')
    # RCR
    ROTATE.addform(None, '0100 0RXB', '0xd1', '11 011 reg')
    ROTATE.addform(None, '0100 0RXB', '0xc1', '11 011 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, '0100 0RXB', '0xd1', '11 011 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd1', '11 011 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd1', '11 011 reg')
    ROTATE.addform(None, '0100 1RX0', '0xc1', '11 011 reg', set(), set(['100']), 8)
    ROTATE.addform(None, '0100 1RX1', '0xc1', '11 011 reg', set(), set(), 8)
    ROTATE.addform(None, '0100 0RXB', '0xd3', '11 011 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd3', '11 011 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd3', '11 011 reg')
    # ROL
    ROTATE.addform(None, '0100 0RXB', '0xd1', '11 000 reg')
    ROTATE.addform(None, '0100 0RXB', '0xc1', '11 000 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, '0100 0RXB', '0xd1', '11 000 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd1', '11 000 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd1', '11 000 reg')
    ROTATE.addform(None, '0100 1RX0', '0xc1', '11 000 reg', set(), set(['100']), 8)
    ROTATE.addform(None, '0100 1RX1', '0xc1', '11 000 reg', set(), set(), 8)
    ROTATE.addform(None, '0100 0RXB', '0xd3', '11 000 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd3', '11 000 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd3', '11 000 reg')
    # ROR
    ROTATE.addform(None, '0100 0RXB', '0xd1', '11 001 reg')
    ROTATE.addform(None, '0100 0RXB', '0xc1', '11 001 reg', set(), set(), 8)
    ROTATE.addform(OSIZE, '0100 0RXB', '0xd1', '11 001 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd1', '11 001 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd1', '11 001 reg')
    ROTATE.addform(None, '0100 1RX0', '0xc1', '11 001 reg', set(), set(['100']), 8)
    ROTATE.addform(None, '0100 1RX1', '0xc1', '11 001 reg', set(), set(), 8)
    ROTATE.addform(None, '0100 0RXB', '0xd3', '11 001 reg')
    ROTATE.addform(None, '0100 1RX0', '0xd3', '11 001 reg', set(), set(['100']))
    ROTATE.addform(None, '0100 1RX1', '0xd3', '11 001 reg')

# Shfit
SHIFT = Instruction('shift')
# 32-bit
if True:
    # SAL/SHL
    SHIFT.addform(None, None, '0xd1', '11 100 reg')
    SHIFT.addform(None, None, '0xc1', '11 100 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, None, '0xd1', '11 100 reg')
    SHIFT.addform(None, None, '0xd3', '11 100 reg')
    # SAR
    SHIFT.addform(None, None, '0xd1', '11 111 reg')
    SHIFT.addform(None, None, '0xc1', '11 111 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, None, '0xd1', '11 111 reg')
    SHIFT.addform(None, None, '0xd3', '11 111 reg')
    # SHR
    SHIFT.addform(None, None, '0xd1', '11 101 reg')
    SHIFT.addform(None, None, '0xc1', '11 101 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, None, '0xd1', '11 101 reg')
    SHIFT.addform(None, None, '0xd3', '11 101 reg')

if True:
    # SAL/SHL
    SHIFT.addform(None, '0100 0RXB', '0xd1', '11 100 reg')
    SHIFT.addform(None, '0100 0RXB', '0xc1', '11 100 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, '0100 0RXB', '0xd1', '11 100 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd1', '11 100 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd1', '11 100 reg')
    SHIFT.addform(None, '0100 1RX0', '0xc1', '11 100 reg', set(), set(['100']), 8)
    SHIFT.addform(None, '0100 1RX1', '0xc1', '11 100 reg', set(), set(), 8)
    SHIFT.addform(None, '0100 0RXB', '0xd3', '11 100 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd3', '11 100 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd3', '11 100 reg')
    # SAR
    SHIFT.addform(None, '0100 0RXB', '0xd1', '11 111 reg')
    SHIFT.addform(None, '0100 0RXB', '0xc1', '11 111 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, '0100 0RXB', '0xd1', '11 111 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd1', '11 111 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd1', '11 111 reg')
    SHIFT.addform(None, '0100 1RX0', '0xc1', '11 111 reg', set(), set(['100']), 8)
    SHIFT.addform(None, '0100 1RX1', '0xc1', '11 111 reg', set(), set(), 8)
    SHIFT.addform(None, '0100 0RXB', '0xd3', '11 111 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd3', '11 111 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd3', '11 111 reg')
    # SHR
    SHIFT.addform(None, '0100 0RXB', '0xd1', '11 101 reg')
    SHIFT.addform(None, '0100 0RXB', '0xc1', '11 101 reg', set(), set(), 8)
    SHIFT.addform(OSIZE, '0100 0RXB', '0xd1', '11 101 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd1', '11 101 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd1', '11 101 reg')
    SHIFT.addform(None, '0100 1RX0', '0xc1', '11 101 reg', set(), set(['100']), 8)
    SHIFT.addform(None, '0100 1RX1', '0xc1', '11 101 reg', set(), set(), 8)
    SHIFT.addform(None, '0100 0RXB', '0xd3', '11 101 reg')
    SHIFT.addform(None, '0100 1RX0', '0xd3', '11 101 reg', set(), set(['100']))
    SHIFT.addform(None, '0100 1RX1', '0xd3', '11 101 reg')

# Test instruction            
TEST = Instruction('test')
# 32-bit
if True:
    # register and register
    TEST.addform(None, None, '0x84', '11 reg reg')
    TEST.addform(None, None, '0x85', '11 reg reg')
    TEST.addform(OSIZE, None, '0x85', '11 reg reg')
    # register and memory
    TEST.addform(None, None, '0x84', 'mod reg r/m')
    TEST.addform(None, None, '0x85', 'mod reg r/m')
    TEST.addform(OSIZE, None, '0x85', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    TEST.addform(None, None, '0xf6', '11 000 reg', set(), set(), 8);
    TEST.addform(None, None, '0xf7', '11 000 reg', set(), set(), 32);
    TEST.addform(OSIZE, None, '0xf7', '11 000 reg', set(), set(), 16);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    TEST.addform(None, None, '0xa8', None, set(), set(), 8)
    TEST.addform(None, None, '0xa9', None, set(), set(), 32)
    TEST.addform(OSIZE, None, '0xa9', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    TEST.addform(None, None, '0xf6', 'mod 000 r/m', set(), set(), 8);
    TEST.addform(None, None, '0xf7', 'mod 000 r/m', set(), set(), 32);
    TEST.addform(OSIZE, None, '0xf7', 'mod 000 r/m', set(), set(), 16);

# 64-bit
if True:
    # register and register
    TEST.addform(None, '0100 0R0B', '0x84', '11 reg reg')
    TEST.addform(None, '0100 0R0B', '0x85', '11 reg reg')
    TEST.addform(OSIZE, '0100 0R0B', '0x85', '11 reg reg')
    # quadreg and quadreg
    TEST.addform(None, '0100 1R0B', '0x85', '11 reg reg')
    # register and memory
    TEST.addform(None, '0100 0RXB', '0x84', 'mod reg r/m')
    TEST.addform(None, '0100 0RXB', '0x85', 'mod reg r/m')
    TEST.addform(OSIZE, '0100 0RXB', '0x85', 'mod reg r/m')
    # quadregister and memory64
    TEST.addform(None, '0100 1RXB', '0x85', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    TEST.addform(None, '0100 000B', '0xf6', '11 000 reg', set(), set(), 8);
    TEST.addform(None, '0100 000B', '0xf7', '11 000 reg', set(), set(), 32);
    TEST.addform(OSIZE, '0100 000B', '0xf7', '11 000 reg', set(), set(), 16);
    # immediate32 to quadreg
    TEST.addform(None, '0100 100B', '0xf7', '11 000 reg', set(), set(), 32);
    # immediate to RAX
    TEST.addform(None, '0100 1000', '0xa9', None, set(), set(), 32)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    TEST.addform(None, '0100 00XB', '0xf6', 'mod 000 r/m', set(), set(), 8);
    TEST.addform(None, '0100 00XB', '0xf7', 'mod 000 r/m', set(), set(), 32);
    TEST.addform(OSIZE, '0100 00XB', '0xf7', 'mod 000 r/m', set(), set(), 16);
    # imm32 to memory
    TEST.addform(None, '0100 10XB', '0xf7', 'mod 000 r/m', set(), set(), 32);

# Xchg instruction
XCHG = Instruction("xchg")
# 32-bit
if True:
    # register1 with register2 1000 011w : 11 reg1 reg2
    XCHG.addform(None, None, '0x86', '11 reg1 reg2')
    XCHG.addform(None, None, '0x87', '11 reg1 reg2')
    XCHG.addform(OSIZE, None, '0x87', '11 reg1 reg2')
    # AX or EAX with reg 1001 0 reg
    XCHG.addform(None, '1001 0reg', '')
    XCHG.addform(OSIZE, '1001 0reg', '')
    # memory with reg 1000 011w : mod reg r/m
    XCHG.addform(SBX, None, '0x86', 'mod reg r/m')
    XCHG.addform(SBX, None, '0x87', 'mod reg r/m')
    XCHG.addform(SBXOSIZE, None, '0x87', 'mod reg r/m')

# 64-bit
if True:
    # register1 with register2 1000 011w : 11 reg1 reg2
    XCHG.addform(None, '0100 0R0B', '0x86', '11 reg1 reg2')
    XCHG.addform(None, '0100 0R0B', '0x87', '11 reg1 reg2')
    XCHG.addform(OSIZE, '0100 0R0B', '0x87', '11 reg1 reg2')
    # quadreg1 with quadreg2
    XCHG.addform(None, '0100 1R0B', '0x87', '11 reg1 reg2', set(['100']), set(['100']))
    # AX or EAX with reg 1001 0 reg, reg cannot be rsp
    XCHG.addform('0x48', '1001 0000', '')
    XCHG.addform('0x48', '1001 0001', '')
    XCHG.addform('0x48', '1001 0010', '')
    XCHG.addform('0x48', '1001 0011', '')
    XCHG.addform('0x48', '1001 0101', '')
    XCHG.addform('0x48', '1001 0110', '')
    XCHG.addform('0x48', '1001 0111', '')
    XCHG.addform('0x49', '1001 0reg', '')
    # memory with reg 1000 011w : mod reg r/m
    XCHG.addform(SBX, '0100 0RXB', '0x86', 'mod reg r/m')
    XCHG.addform(SBX, '0100 0RXB', '0x87', 'mod reg r/m')
    XCHG.addform(SBXOSIZE, '0100 0RXB', '0x87', 'mod reg r/m')
    # memory64 with reg64
    XCHG.addform(SBX, '0100 1RXB', '0x87', 'mod reg r/m', set(['100']))

# Xor instruction            
XOR = Instruction('xor')
# 32-bit
if True:
    # register1 to register2 0000 000w : 11 reg1 reg2
    XOR.addform(None, None, '0x30', '11 reg1 reg2')
    XOR.addform(None, None, '0x31', '11 reg1 reg2')
    XOR.addform(OSIZE, None, '0x31', '11 reg1 reg2') # 16-bit
    # register2 to register1 0000 001w : 11 reg1 reg2
    XOR.addform(None, None, '0x32', '11 reg1 reg2')
    XOR.addform(None, None, '0x33', '11 reg1 reg2')
    XOR.addform(OSIZE, None, '0x33', '11 reg1 reg2') # 16-bit
    # memory to register 0010 001w : mod reg r/m
    XOR.addform(None, None, '0x32', 'mod reg r/m')
    XOR.addform(None, None, '0x33', 'mod reg r/m')
    XOR.addform(OSIZE, None, '0x33', 'mod reg r/m') # 16-bit
    # register to memory 0000 000w : mod reg r/m
    XOR.addform(SBX, None, '0x30', 'mod reg r/m')
    XOR.addform(SBX, None, '0x31', 'mod reg r/m')
    XOR.addform(SBXOSIZE, None, '0x31', 'mod reg r/m')
    # immediate to register 1000 00sw : 11 000 reg : immediate data
    XOR.addform(None, None, '0x80', '11 110 reg', set(), set(), 8);
    XOR.addform(None, None, '0x81', '11 110 reg', set(), set(), 32);
    XOR.addform(OSIZE, None, '0x81', '11 110 reg', set(), set(), 16);
    XOR.addform(None, None, '0x83', '11 110 reg', set(), set(), 8);
    XOR.addform(OSIZE, None, '0x83', '11 110 reg', set(), set(), 8);
    # immediate to AL, AX, or EAX 0000 010w : immediate data
    XOR.addform(None, None, '0x34', None, set(), set(), 8)
    XOR.addform(None, None, '0x35', None, set(), set(), 32)
    XOR.addform(OSIZE, None, '0x35', None, set(), set(), 16)
    # immediate to memory 1000 00sw : mod 000 r/m : immediate data
    XOR.addform(SBX, None, '0x80', 'mod 110 r/m', set(), set(), 8);
    XOR.addform(SBX, None, '0x81', 'mod 110 r/m', set(), set(), 32);
    XOR.addform(SBXOSIZE, None, '0x81', 'mod 110 r/m', set(), set(), 16);
    XOR.addform(SBX, None, '0x83', 'mod 110 r/m', set(), set(), 8);
    XOR.addform(SBXOSIZE, None, '0x83', 'mod 110 r/m', set(), set(), 8);

# 64-bit
if True:
    # register1 to register2 0100 0R0B : 0000 000w : 11 reg1 reg2
    XOR.addform(None, '0100 0R0B', '0x30', '11 reg1 reg2')
    XOR.addform(None, '0100 0R0B', '0x31', '11 reg1 reg2')
    XOR.addform(OSIZE, '0100 0R0B', '0x31', '11 reg1 reg2') # 16-bit
    # qwordregister1 to qwordregister2 0100 1R0B 0000 0000 : 11 qwordreg1 qwordreg2
    # rsp should never be a target register
    XOR.addform(None, '0100 1R00', '0x31', '11 reg1 reg2', set(), set(['100']))
    XOR.addform(None, '0100 1R01', '0x31', '11 reg1 reg2')
    # register2 to register1 0100 0R0B : 0000 001w : 11 reg1 reg2
    XOR.addform(None, '0100 0R0B', '0x32', '11 reg1 reg2')
    XOR.addform(None, '0100 0R0B', '0x33', '11 reg1 reg2')
    XOR.addform(OSIZE, '0100 0R0B', '0x33', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 0000 0010 : 11 qwordreg1 qwordreg2
    XOR.addform(None, '0100 100B', '0x33', '11 reg1 reg2', set(['100']), set())
    XOR.addform(None, '0100 110B', '0x33', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 001w : mod reg r/m
    XOR.addform(None, '0100 0RXB', '0x32', 'mod reg r/m')
    XOR.addform(None, '0100 0RXB', '0x33', 'mod reg r/m')
    XOR.addform(OSIZE, '0100 0RXB', '0x33', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB : 0000 0000 : mod qwordreg r/m
    XOR.addform(None, '0100 10XB', '0x33', 'mod reg r/m', set(['100']))
    XOR.addform(None, '0100 11XB', '0x33', 'mod reg r/m')
    # register to memory 0100 0RXB : 0000 000w : mod reg r/m
    XOR.addform(SBX, '0100 0RXB', '0x30', 'mod reg r/m')
    XOR.addform(SBX, '0100 0RXB', '0x31', 'mod reg r/m')
    XOR.addform(SBXOSIZE, '0100 0RXB', '0x31', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB : 0000 0110 : mod qwordreg r/m
    XOR.addform(SBX, '0100 1RXB', '0x31', 'mod reg r/m')
    # immediate to register 0100 0000B : 1000 00sw : 11 000 reg : immediate data
    XOR.addform(None, '0100 000B', '0x80', '11 110 reg', set(), set(), 8);
    XOR.addform(None, '0100 000B', '0x81', '11 110 reg', set(), set(), 32);
    XOR.addform(OSIZE, '0100 000B', '0x81', '11 110 reg', set(), set(), 16);
    XOR.addform(None, '0100 000B', '0x83', '11 110 reg', set(), set(), 8);
    XOR.addform(OSIZE, '0100 000B', '0x83', '11 110 reg', set(), set(), 8);
    # immediate32 to qwordregister 0100 100B : 1000 0001 : 11 010 qwordreg : imm
    XOR.addform(None, '0100 1000', '0x81', '11 110 reg', set(), set(['100']), 32)
    XOR.addform(None, '0100 1001', '0x81', '11 110 reg', set(), set(), 32)
    # immediate8 to qword reg
    XOR.addform(None, '0100 100B', '0x83', '11 110 reg', set(), set(), 8);
    # immediate to RAX 0100 1000 : 0000 0110 : imm32
    XOR.addform(None, '0100 1000', '0x35', None, set(), set(), 32)
    # immediate to memory 0100 00XB : 1000 00sw : mod 000 r/m : immediate
    XOR.addform(SBX, '0100 00XB', '0x80', 'mod 110 r/m', set(), set(), 8);
    XOR.addform(SBX, '0100 00XB', '0x81', 'mod 110 r/m', set(), set(), 32);
    XOR.addform(SBXOSIZE, '0100 00XB', '0x81', 'mod 110 r/m', set(), set(), 16);
    # immediate32 to memory64 0100 10XB : 1000 0001 : mod 010 r/m : imm32
    XOR.addform(SBX, '0100 10XB', '0x81', 'mod 110 r/m', set(), set(), 32)
    # immediate8 to memory64 0100 10XB : 1000 0110 : mod 010 r/m : imm8
    XOR.addform(SBX, '0100 W0XB', '0x83', 'mod 110 r/m', set(), set(), 8)

# BT
BT = Instruction("bt")
# 32-bit
if True:
    # register1, register2 0000 1111 : 1010 0011 : 11 reg2 reg1
    BT.addform(None, None, '0x0f 0xa3', '11 reg1 reg2')
    BT.addform(OSIZE, None, '0x0f 0xa3', '11 reg1 reg2')
    # memory, reg 0000 1111 : 1010 0011 : mod reg r/m
    BT.addform(None, None, '0x0f 0xa3', 'mod reg r/m')
    BT.addform(OSIZE, None, '0x0f 0xa3', 'mod reg r/m')
    # register, immediate 0000 1111 : 1011 1010 : 11 100 reg: imm8 data
    BT.addform(None, None, '0x0f 0xba', '11 100 r/m', set(), set(), 8)
    BT.addform(OSIZE, None, '0x0f 0xba', '11 100 r/m', set(), set(), 8)
    # memory, immediate 0000 1111 : 1011 1010 : mod 100 r/m : imm8 data
    BT.addform(None, None, '0x0f 0xba', 'mod 100 r/m', set(), set(), 8)
    BT.addform(OSIZE, None, '0x0f 0xba', 'mod 100 r/m', set(), set(), 8)

# 64-bit
if True:
    BT.addform(None, '0100 WRXB', '0x0f 0xa3', '11 reg1 reg2')
    BT.addform(OSIZE, '0100 0RXB', '0x0f 0xa3', '11 reg1 reg2')
    BT.addform(None, '0100 WRXB', '0x0f 0xa3', 'mod reg r/m')
    BT.addform(OSIZE, '0100 0RXB', '0x0f 0xa3', 'mod reg r/m')
    BT.addform(None, '0100 WRXB', '0x0f 0xba', '11 100 r/m', set(), set(), 8)
    BT.addform(None, '0100 WRXB', '0x0f 0xba', 'mod 100 r/m', set(), set(), 8)

# BTS
BTS = Instruction("bts")
# 32-bit
if True:
    # register1, register2 0000 1111 : 1010 0011 : 11 reg2 reg1
    BTS.addform(None, None, '0x0f 0xab', '11 reg1 reg2')
    BTS.addform(OSIZE, None, '0x0f 0xab', '11 reg1 reg2')
    # memory, reg 0000 1111 : 1010 0011 : mod reg r/m
    BTS.addform(SBX, None, '0x0f 0xab', 'mod reg r/m')
    BTS.addform(SBXOSIZE, None, '0x0f 0xab', 'mod reg r/m')
    # register, immediate 0000 1111 : 1011 1010 : 11 101 reg: imm8 data
    BTS.addform(None, None, '0x0f 0xba', '11 101 r/m', set(), set(), 8)
    BTS.addform(OSIZE, None, '0x0f 0xba', '11 101 r/m', set(), set(), 8)
    # memory, immediate 0000 1111 : 1011 1010 : mod 101 r/m : imm8 data
    BTS.addform(SBX, None, '0x0f 0xba', 'mod 101 r/m', set(), set(), 8)
    BTS.addform(SBXOSIZE, None, '0x0f 0xba', 'mod 101 r/m', set(), set(), 8)

# 64-bit
if True:
    BTS.addform(None, '0100 WRXB', '0x0f 0xa3', '11 reg1 reg2')
    BTS.addform(OSIZE, '0100 0RXB', '0x0f 0xa3', '11 reg1 reg2')
    BTS.addform(SBX, '0100 WRXB', '0x0f 0xa3', 'mod reg r/m')
    BTS.addform(SBXOSIZE, '0100 0RXB', '0x0f 0xa3', 'mod reg r/m')
    BTS.addform(None, '0100 WRXB', '0x0f 0xba', '11 100 r/m', set(), set(), 8)
    BTS.addform(SBX, '0100 WRXB', '0x0f 0xba', 'mod 100 r/m', set(), set(), 8)

# BSR
BSR = Instruction("bsr")
# 32-bit
if True:
    BSR.addform(None, None, '0x0f 0xbd', '11 reg1 reg2')
    BSR.addform(OSIZE, None, '0x0f 0xbd', '11 reg1 reg2')
    BSR.addform(None, None, '0x0f 0xbd', 'mod reg r/m')
    BSR.addform(OSIZE, None, '0x0f 0xbd', 'mod reg r/m')

# 64-bit
if True:
    BSR.addform(None, '0100 0RXB', '0x0f 0xbd', '11 reg1 reg2')
    BSR.addform(None, '0100 10XB', '0x0f 0xbd', '11 reg1 reg2', set(['100']))
    BSR.addform(None, '0100 11XB', '0x0f 0xbd', '11 reg1 reg2')
    BSR.addform(OSIZE, '0100 0RXB', '0x0f 0xbd', '11 reg1 reg2')
    BSR.addform(None, '0100 0RXB', '0x0f 0xbd', 'mod reg r/m')
    BSR.addform(None, '0100 10XB', '0x0f 0xbd', 'mod reg r/m', set(['100']))
    BSR.addform(None, '0100 11XB', '0x0f 0xbd', 'mod reg r/m')
    BSR.addform(OSIZE, '0100 0RXB', '0x0f 0xbd', 'mod reg r/m')

# REPMOVS
REPMOVS = Instruction("repmovs")
if True:
    REPMOVS.addform('0x89 0xff 0xf3', None, '0xa4')
    REPMOVS.addform('0x89 0xff 0xf3', None, '0xa5')
    REPMOVS.addform('0x89 0xff 0xf3 0x66', None, '0xa5')
    REPMOVS.addform('0x89 0xff 0xf3', '0100 1000', '0xa5')

# SHLD
SHLD = Instruction("shld")
# 32-bit
if True:
    SHLD.addform(None, None, '0x0f 0xa5', '11 reg1 reg2')
    SHLD.addform(OSIZE, None, '0x0f 0xa5', '11 reg1 reg2')

# 64-bit
if True:
    SHLD.addform(None, '0100 0RXB', '0x0f 0xa5', '11 reg1 reg2')
    SHLD.addform(OSIZE, '0100 0RXB', '0x0f 0xa5', '11 reg1 reg2')
    SHLD.addform(None, '0100 1RX0', '0x0f 0xa5', '11 reg1 reg2', set(), set(['100']))
    SHLD.addform(None, '0100 1RX1', '0x0f 0xa5', '11 reg1 reg2')

# SHRD
SHRD = Instruction("shrd")
# 32-bit
if True:
    SHRD.addform(None, None, '0x0f 0xad', '11 reg1 reg2')
    SHRD.addform(OSIZE, None, '0x0f 0xad', '11 reg1 reg2')

# 64-bit
if True:
    SHRD.addform(None, '0100 0RXB', '0x0f 0xad', '11 reg1 reg2')
    SHRD.addform(OSIZE, '0100 0RXB', '0x0f 0xad', '11 reg1 reg2')
    SHRD.addform(None, '0100 1RX0', '0x0f 0xad', '11 reg1 reg2', set(), set(['100']))
    SHRD.addform(None, '0100 1RX1', '0x0f 0xad', '11 reg1 reg2')

# NOP
NOP = Instruction("nop")
if True:
    NOP.addform(None, None, '0x90')
    NOP.addform(None, None, '0x66 0x90')
    NOP.addform(None, None, '0x0f 0x1f 0x00')
    NOP.addform(None, None, '0x0f 0x1f 0x40 0x00')
    NOP.addform(None, None, '0x0f 0x1f 0x44 0x00 0x00')
    NOP.addform(None, None, '0x66 0x0f 0x1f 0x44 0x00 0x00')
    NOP.addform(None, None, '0x0f 0x1f 0x80 0x00 0x00 0x00 0x00')
    NOP.addform(None, None, '0x0f 0x1f 0x84 0x00 0x00 0x00 0x00 0x00')
    NOP.addform(None, None, '0x66 0x0f 0x1f 0x84 0x00 0x00 0x00 0x00 0x00')
    NOP.addform(None, None, '0x66 0x66 0x0f 0x1f 0x84 0x00 0x00 0x00 0x00 0x00')
    NOP.addform(None, None, '0x66 0x66 0x66 0x0f 0x1f 0x84 0x00 0x00 0x00 0x00 0x00')
# ENTER
ENTER = Instruction("enter")
if True:
    ENTER.addform(None, None, '0xc8', None, set(), set(), 16, '0x00 0x89 0xe4') # movl %esp, %esp

# LEAVE
LEAVE = Instruction("leave")
if True:
    LEAVE.addform(None, None, '0xc9', None, set(), set(), 0, '0x89 0xe4') # movl %esp, %esp

# CQO
CQO = Instruction("cqo")
if True:
    CQO.addform(None, '0100 1000', '0x99')

# CDQ
CDQ = Instruction("cdq")
if True:
    CDQ.addform(None, None, '0x99')

# CLC
CLC = Instruction("clc")
if True:
    CLC.addform(None, None, '0xf8')

# CLD
CLD = Instruction("cld")
if True:
    CLD.addform(None, None, '0xfc')

# CPUID
CPUID = Instruction("cpuid")
if True:
    CPUID.addform(None, None, '0x0f 0xa2')

# HLT
HLT = Instruction("hlt", "terminator")
if True:
    HLT.addform(None, None, '0xf4')

# INT3
INT3 = Instruction("int3", "terminator")
if True:
    INT3.addform(None, None, '0xcc')

# LEA
LEA = Instruction("lea")
# 32-bit
if True:
    LEA.addform(None, None, '0x8d', 'mod reg r/m')
    LEA.addform(OSIZE, None, '0x8d', 'mod reg r/m')

# 64-bit
if True:
    LEA.addform(None, '0100 0RXB', '0x8d', 'mod reg r/m')
    LEA.addform(OSIZE, '0100 0RXB', '0x8d', 'mod reg r/m')
    LEA.addform(None, '0100 10XB', '0x8d', 'mod reg r/m', set(['100']))
    LEA.addform(None, '0100 11XB', '0x8d', 'mod reg r/m')

# MOV
MOV = Instruction("mov")
# 32-bit
if True:
    # register1 to register2 1000 100w : 11 reg1 reg2
    MOV.addform(None, None, '0x88', '11 reg1 reg2')
    MOV.addform(None, None, '0x89', '11 reg1 reg2')
    MOV.addform(OSIZE, None, '0x89', '11 reg1 reg2')
    # register2 to register1 1000 101w : 11 reg1 reg2
    MOV.addform(None, None, '0x8a', '11 reg1 reg2')
    MOV.addform(None, None, '0x8b', '11 reg1 reg2')
    MOV.addform(OSIZE, None, '0x8b', '11 reg1 reg2')
    # memory to reg 1000 101w : mod reg r/m
    MOV.addform(None, None, '0x8a', 'mod reg r/m')
    MOV.addform(None, None, '0x8b', 'mod reg r/m')
    MOV.addform(OSIZE, None, '0x8b', 'mod reg r/m')
    # reg to memory 1000 100w : mod reg r/m
    MOV.addform(SBX, None, '0x88', 'mod reg r/m')
    MOV.addform(SBX, None, '0x89', 'mod reg r/m')
    MOV.addform(SBXOSIZE, None, '0x89', 'mod reg r/m')
    # immediate to register 1100 011w : 11 000 reg : immediate data
    MOV.addform(None, None, '0xc6', '11 000 reg', set(), set(), 8)
    MOV.addform(None, None, '0xc7', '11 000 reg', set(), set(), 32)
    MOV.addform(OSIZE, None, '0xc7', '11 000 reg', set(), set(), 16)
    # immediate to register (alternate encoding) 1011 w reg : immediate data
    MOV.addform(None, '1011 0reg', '', None, set(), set(), 8)
    MOV.addform(None, '1011 1reg', '', None, set(), set(), 32)
    MOV.addform(OSIZE, '1011 1reg', '', None, set(), set(), 16)
    # immediate to memory 1100 011w : mod 000 r/m : immediate data
    MOV.addform(SBX, None, '0xc6', 'mod 000 reg', set(), set(), 8)
    MOV.addform(SBX, None, '0xc7', 'mod 000 reg', set(), set(), 32)
    MOV.addform(SBXOSIZE, None, '0xc7', 'mod 000 reg', set(), set(), 16)
    # memory to AL, AX, or EAX 1010 000w : full displacement, not available in 64-bit
    # AL, AX, or EAX to memory 1010 001w : full displacement, not available in 64-bit

if True:
    # register1 to register2 1000 100w : 11 reg1 reg2
    MOV.addform(None, '0100 0R0B', '0x88', '11 reg1 reg2')
    MOV.addform(None, '0100 0R0B', '0x89', '11 reg1 reg2')
    MOV.addform(OSIZE, '0100 0R0B', '0x89', '11 reg1 reg2')
    # qwordregister1 to qwordregister2 0100 1R0B 1000 1001 : 11 qwordeg1 qwordreg2
    MOV.addform(None, '0100 1R00', '0x89', '11 reg1 reg2', set(), set(['100']))
    MOV.addform(None, '0100 1R01', '0x89', '11 reg1 reg2')
    # register2 to register1 1000 101w : 11 reg1 reg2
    MOV.addform(None, '0100 0R0B', '0x8a', '11 reg1 reg2')
    MOV.addform(None, '0100 0R0B', '0x8b', '11 reg1 reg2')
    MOV.addform(OSIZE, '0100 0R0B', '0x8b', '11 reg1 reg2')
    # qwordregister2 to qwordregister1 0100 1R0B 1000 1011 : 11 qwordreg1 qwordreg2
    MOV.addform(None, '0100 100B', '0x8b', '11 reg1 reg2', set(['100']))
    MOV.addform(None, '0100 110B', '0x8b', '11 reg1 reg2')
    # memory to reg 1000 101w : mod reg r/m
    MOV.addform(None, '0100 0RXB', '0x8a', 'mod reg r/m')
    MOV.addform(None, '0100 0RXB', '0x8b', 'mod reg r/m')
    MOV.addform(OSIZE, '0100 0RXB', '0x8b', 'mod reg r/m')
    # memory64 to qwordregister 0100 1RXB 1000 1011 : mod qwordreg r/m
    MOV.addform(None, '0100 10XB', '0x8b', 'mod reg r/m', set(['100']))
    MOV.addform(None, '0100 11XB', '0x8b', 'mod reg r/m')
    # reg to memory 1000 100w : mod reg r/m
    MOV.addform(SBX, '0100 0RXB', '0x88', 'mod reg r/m')
    MOV.addform(SBX, '0100 0RXB', '0x89', 'mod reg r/m')
    MOV.addform(SBXOSIZE, '0100 0RXB', '0x89', 'mod reg r/m')
    # qwordregister to memory64 0100 1RXB 1000 1001 : mod qwordreg r/m
    MOV.addform(SBX, '0100 1RXB', '0x89', 'mod reg r/m')
    # immediate to register 1100 011w : 11 000 reg : immediate data
    MOV.addform(None, '0100 000B', '0xc6', '11 000 reg', set(), set(), 8)
    MOV.addform(None, '0100 000B', '0xc7', '11 000 reg', set(), set(), 32)
    MOV.addform(OSIZE, '0100 000B', '0xc7', '11 000 reg', set(), set(), 16)
    # immediate32 to qwordregister (zero extend) 0100 100B 1100 0111 : 11 000 qwordreg : imm32
    MOV.addform(None, '0100 1000', '0xc7', '11 000 reg', set(), set(['100']), 32)
    MOV.addform(None, '0100 1001', '0xc7', '11 000 reg', set(), set(), 32)
    # immediate to register (alternate encoding) 1011 w reg : immediate data
    MOV.addform('0x48', '1011 0reg', '', None, set(), set(), 8)
    MOV.addform('0x49', '1011 0reg', '', None, set(), set(), 8)
    MOV.addform('0x48', '1011 1000', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1001', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1010', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1011', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1101', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1110', '', None, set(), set(), 64)
    MOV.addform('0x48', '1011 1111', '', None, set(), set(), 64)
    MOV.addform('0x49', '1011 1reg', '', None, set(), set(), 64)
    MOV.addform2(None, '0100 000B', '1011 1reg', set(), 32)
    # immediate to memory 0100 00XB : 1100 011w : mod 000 r/m : imm
    MOV.addform(SBX, '0100 00XB', '0xc6', 'mod 000 reg', set(), set(), 8)
    MOV.addform(SBX, '0100 00XB', '0xc7', 'mod 000 reg', set(), set(), 32)
    MOV.addform(SBXOSIZE, '0100 00XB', '0xc7', 'mod 000 reg', set(), set(), 16)
    # immediate32 to memory64 (zero extend) 0100 10XB 1100 0111 : mod 000 r/m : imm32
    MOV.addform(SBX, '0100 10XB', '0xc7', 'mod 000 reg', set(), set(), 32)
    # memory64 to RAX 0100 1000 1010 0001 : displacement64
    MOV.addform(None, '0100 1000', '0xa1', None, set(), set(), 64)
    MOV.addform(None, '0100 1000', '0xa3', None, set(), set(), 64)
    # RAX to memory64 0100 1000 1010 0011 : displacement64, no need

# CMOV
CMOV = Instruction("cmov")
# 32-bit
if True:
    CMOV.addform(None, None, '0000 1111 0100 tnnn', '11 reg1 reg2', set(), set(), 0, None, True)
    CMOV.addform(OSIZE, None, '0000 1111 0100 tnnn', '11 reg1 reg2', set(), set(), 0, None, True)
    CMOV.addform(None, None, '0000 1111 0100 tnnn', 'mod reg r/m', set(), set(), 0, None, True)
    CMOV.addform(OSIZE, None, '0000 1111 0100 tnnn', 'mod reg r/m', set(), set(), 0, None, True)

# 64-bit
if True:
    CMOV.addform(None, '0100 0RXB', '0000 1111 0100 tnnn', '11 reg1 reg2',
                 set(), set(), 0, None, True)
    CMOV.addform(OSIZE, '0100 0RXB', '0000 1111 0100 tnnn', '11 reg1 reg2',
                 set(), set(), 0, None, True)
    CMOV.addform(None, '0100 10XB', '0000 1111 0100 tnnn', '11 reg1 reg2',
                 set(['100']), set(), 0, None, True)
    CMOV.addform(None, '0100 11XB', '0000 1111 0100 tnnn', '11 reg1 reg2',
                 set(), set(), 0, None, True)
    CMOV.addform(None, '0100 0RXB', '0000 1111 0100 tnnn', 'mod reg r/m',
                 set(), set(), 0, None, True)
    CMOV.addform(OSIZE, '0100 0RXB', '0000 1111 0100 tnnn', 'mod reg r/m',
                 set(), set(), 0, None, True)
    CMOV.addform(None, '0100 10XB', '0000 1111 0100 tnnn', 'mod reg r/m',
                 set(['100']), set(), 0, None, True)
    CMOV.addform(OSIZE, '0100 11XB', '0000 1111 0100 tnnn', 'mod reg r/m',
                 set(), set(), 0, None, True)

# SETCC
SETCC = Instruction("setcc")
# 32-bit
if True:
    # register 0000 1111 : 1001 tttn : 11 000 reg
    SETCC.addform(None, None, '0000 1111 1001 tttn', '11 reg1 reg2', set(), set(), 0, None, True)

# 64-bit
if True:
    # register 0100 000B 0000 1111 : 1001 tttn : 11 000 reg
    SETCC.addform(None, '0100 000B', '0000 1111 1001 tttn', '11 reg1 reg2',
                  set(), set(), 0, None, True)

# MOVZX
MOVZX = Instruction("mov")
# 32-bit
if True:
    # register2 to register1 0000 1111 : 1011 011w : 11 reg1 reg2
    MOVZX.addform(OSIZE, None, '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, None, '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, None, '0x0f 0xb7', '11 reg1 reg2')
    # memory to register 0000 1111 : 1011 011w : mod reg r/m
    MOVZX.addform(OSIZE, None, '0x0f 0xb6', 'mod reg r/m')    
    MOVZX.addform(None, None, '0x0f 0xb6', 'mod reg r/m')
    MOVZX.addform(None, None, '0x0f 0xb7', 'mod reg r/m')

# 64-bit
if True:
    # register2 to register1 0000 1111 : 1011 011w : 11 reg1 reg2
    MOVZX.addform(OSIZE, '0100 0R0B', '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, '0100 0R0B', '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, '0100 0R0B', '0x0f 0xb7', '11 reg1 reg2')
    # dwordregister2 to qwordregister1
    # 0100 1R0B 0000 1111 : 1011 0111 : 11 qwordreg1 dwordreg2
    MOVZX.addform(None, '0100 1R0B', '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, '0100 1R0B', '0x0f 0xb7', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 1111 : 1011 011w : mod reg r/m
    MOVZX.addform(OSIZE, '0100 0RXB', '0x0f 0xb6', 'mod reg r/m')    
    MOVZX.addform(None, '0100 0RXB', '0x0f 0xb6', 'mod reg r/m')
    MOVZX.addform(None, '0100 0RXB', '0x0f 0xb7', 'mod reg r/m')
    # memory32 to qwordregister 0100 1RXB 0000 1111 : 1011 0111 : mod qwordreg r/m
    MOVZX.addform(None, '0100 1R0B', '0x0f 0xb6', '11 reg1 reg2')
    MOVZX.addform(None, '0100 1R0B', '0x0f 0xb7', '11 reg1 reg2')

# MOVSX
MOVSX = Instruction("movs")
# 32-bit
if True:
    # register2 to register1
    MOVSX.addform(OSIZE, None, '0x0f 0xbe', '11 reg1 reg2')
    MOVSX.addform(None, None, '0x0f 0xbe', '11 reg1 reg2')
    MOVSX.addform(None, None, '0x0f 0xbf', '11 reg1 reg2')
    # memory to register
    MOVSX.addform(OSIZE, None, '0x0f 0xbe', 'mod reg r/m')
    MOVSX.addform(None, None, '0x0f 0xbe', 'mod reg r/m')
    MOVSX.addform(None, None, '0x0f 0xbf', 'mod reg r/m')

# 64-bit
if True:
    # register2 to register1 0000 1111 : 1011 011w : 11 reg1 reg2
    MOVSX.addform(OSIZE, '0100 0R0B', '0x0f 0xbe', '11 reg1 reg2')
    MOVSX.addform(None, '0100 0R0B', '0x0f 0xbe', '11 reg1 reg2')
    MOVSX.addform(None, '0100 0R0B', '0x0f 0xbf', '11 reg1 reg2')
    # dwordregister2 to qwordregister1
    # 0100 1R0B 0000 1111 : 1011 0111 : 11 qwordreg1 dwordreg2
    MOVSX.addform(None, '0100 1R0B', '0x0f 0xbe', '11 reg1 reg2')
    MOVSX.addform(None, '0100 1R0B', '0x0f 0xbf', '11 reg1 reg2')
    # memory to register 0100 0RXB : 0000 1111 : 1011 011w : mod reg r/m
    MOVSX.addform(OSIZE, '0100 0RXB', '0x0f 0xbe', 'mod reg r/m')
    MOVSX.addform(None, '0100 0RXB', '0x0f 0xbe', 'mod reg r/m')
    MOVSX.addform(None, '0100 0RXB', '0x0f 0xbf', 'mod reg r/m')
    # memory32 to qwordregister 0100 1RXB 0000 1111 : 1011 0111 : mod qwordreg r/m
    MOVSX.addform(None, '0100 1RXB', '0x0f 0xbe', 'mod reg r/m')
    MOVSX.addform(None, '0100 1RXB', '0x0f 0xbf', 'mod reg r/m')
    MOVSX.addform(None, '0100 1R0B', '0x63', '11 reg1 reg2')
    MOVSX.addform(None, '0100 1RXB', '0x63', 'mod reg r/m')

# Push
PUSH = Instruction("push")
# 32-bit
if True:
    # register 1111 1111 : 11 110 reg
    PUSH.addform(None, None, '0xff', '11 110 reg')
    PUSH.addform(OSIZE, None, '0xff', '11 110 reg')
    # register (alternate encoding) 0101 0 reg
    PUSH.addform(None, '0101 0reg', '')
    PUSH.addform(OSIZE, '0101 0reg', '')
    # memory 1111 1111 : mod 110 r/m
    PUSH.addform(None, None, '0xff', 'mod 110 r/m')
    PUSH.addform(OSIZE, None, '0xff', 'mod 110 r/m')
    # immediate 0110 10s0 : immediate data
    PUSH.addform(None, None, '0x6a', None, set(), set(), 8)
    PUSH.addform(None, None, '0x68', None, set(), set(), 32)
    PUSH.addform(OSIZE, None, '0x68', None, set(), set(), 16)

# 64-bit
if True:
    # register 1111 1111 : 11 110 reg
    PUSH.addform(None, '0100 W00B', '0xff', '11 110 reg')
    PUSH.addform(OSIZE, '0100 000B', '0xff', '11 110 reg')
    # register (alternate encoding) 0101 0 reg
    PUSH.addform2(None, '0100 W00B', '0101 0reg', '')
    # memory 1111 1111 : mod 110 r/m
    PUSH.addform(None, '0100 W00B', '0xff', 'mod 110 r/m')
    PUSH.addform(OSIZE, '0100 000B', '0xff', 'mod 110 r/m')

# Pop
POP = Instruction("pop")
# 32-bit
if True:
    # register 1000 1111 : 11 000 reg
    POP.addform(None, None, '0x8f', '11 000 reg')
    POP.addform(OSIZE, None, '0x8f', '11 000 reg')
    # register (alternate encoding) 0101 1 reg
    POP.addform(None, '0101 1reg', '')
    POP.addform(OSIZE, '0101 1reg', '')
    # memory 1000 1111 : mod 000 r/m
    POP.addform(SBX, None, '0x8f', 'mod 000 r/m')
    POP.addform(SBXOSIZE, None, '0x8f', 'mod 000 r/m')

if True:
    # wordregister 0101 0101 : 0100 000B : 1000 1111 : 11 000 reg16
    # wordregister (alternate encoding) 0101 0101 : 0100 000B : 0101 1 reg16
    POP.addform(None, '0100 W000', '0x8f', '11 000 reg', set(), set(['100']))
    POP.addform(None, '0100 W001', '0x8f', '11 000 reg')
    POP.addform(OSIZE, '0100 000B', '0x8f', '11 000 reg')
    # qwordregister 0100 W00BS : 1000 1111 : 11 000 reg64
    # qwordregister (alternate encoding) 0100 W00B : 0101 1 reg64
    POP.addform2(None, '0100 W000', '0101 1reg', set(['0x5c']))
    POP.addform2(None, '0100 W001', '0101 1reg')
    # memory64 0100 W0XBS : 1000 1111 : mod 000 r/m
    # memory16 0101 0101 : 0100 00XB 1000 1111 : mod 000 r/m
    POP.addform(SBX, '0100 00XB', '0x8f', 'mod 000 r/m')
    POP.addform(SBXOSIZE, '0100 00XB', '0x8f', 'mod 000 r/m')

# MOVAPS
MOVAPS = Instruction("movaps")
# 32-bit
if True:
    MOVAPS.addform(None, None, '0x0f 0x28', '11 xmm1 xmm2')
    MOVAPS.addform(None, None, '0x0f 0x28', 'mod xmm1 r/m')
    MOVAPS.addform(None, None, '0x0f 0x29', '11 xmm1 xmm2')
    MOVAPS.addform(SBX, None, '0x0f 0x29', 'mod xmm1 r/m')

# 64-bit
if  True:
    MOVAPS.addform(None, '0100 WRXB', '0x0f 0x28', '11 xmm1 xmm2')
    MOVAPS.addform(None, '0100 WRXB', '0x0f 0x28', 'mod xmm1 r/m')
    MOVAPS.addform(None, '0100 WRXB', '0x0f 0x29', '11 xmm1 xmm2')
    MOVAPS.addform(SBX, '0100 WRXB', '0x0f 0x29', 'mod xmm1 r/m')

# MOVSS
MOVSS = Instruction("movss")
# 32-bit
if True:
    MOVSS.addform('0xf3', None, '0x0f 0x10', '11 xmm1 xmm2')
    MOVSS.addform('0xf3', None, '0x0f 0x10', 'mod xmm1 r/m')
    MOVSS.addform('0xf3', None, '0x0f 0x11', '11 xmm1 xmm2')
    MOVSS.addform('0x67 0xf3', None, '0x0f 0x11', 'mod xmm1 r/m')

# 64-bit
if  True:
    MOVSS.addform('0xf3', '0100 WRXB', '0x0f 0x10', '11 xmm1 xmm2')
    MOVSS.addform('0xf3', '0100 WRXB', '0x0f 0x10', 'mod xmm1 r/m')
    MOVSS.addform('0xf3', '0100 WRXB', '0x0f 0x11', '11 xmm1 xmm2')
    MOVSS.addform('0x67 0xf3', '0100 WRXB', '0x0f 0x11', 'mod xmm1 r/m')

# MOVQ
MOVQ = Instruction("movq")
# 32-bit
if True:
    MOVQ.addform('0xf3', None, '0x0f 0x7e', '11 xmm1 xmm2')

# 64-bit
if True:
    MOVQ.addform('0xf3', '0100 WRXB', '0x0f 0x7e', '11 xmm1 xmm2')

# SHUFPS
SHUFPS = Instruction("shufps")
# 32-bit
if True:
    SHUFPS.addform(None, None, '0x0f 0xc6', '11 reg r/m', set(), set(), 8)
    SHUFPS.addform(None, None, '0x0f 0xc6', 'mod reg r/m', set(), set(), 8)

# 64-bit
if True:
    SHUFPS.addform(None, '0100 WRXB', '0x0f 0xc6', '11 reg r/m', set(), set(), 8)
    SHUFPS.addform(None, '0100 WRXB', '0x0f 0xc6', 'mod reg r/m', set(), set(), 8)

# CVTSI2SS
CVTSI2SS = Instruction("cvtsi2ss")
# 32-bit
if True:
    CVTSI2SS.addform('0xf3', None, '0x0f 0x2a', '11 reg r/m')
    CVTSI2SS.addform('0xf3', None, '0x0f 0x2a', 'mod reg r/m')

# 64-bit
if True:
    CVTSI2SS.addform('0xf3', '0100 WRXB', '0x0f 0x2a', '11 reg r/m')
    CVTSI2SS.addform('0xf3', '0100 WRXB', '0x0f 0x2a', 'mod reg r/m')

# CVTTSS2SI
CVTTSS2SI = Instruction("cvttss2si")
# 32-bit
if True:
    CVTTSS2SI.addform('0xf3', None, '0x0f 0x2c', '11 reg r/m')
    CVTTSS2SI.addform('0xf3', None, '0x0f 0x2c', 'mod reg r/m')

# 64-bit
if True:
    CVTTSS2SI.addform('0xf3', '0100 0RXB', '0x0f 0x2c', '11 reg r/m')
    CVTTSS2SI.addform('0xf3', '0100 10XB', '0x0f 0x2c', '11 reg r/m', set(['100']))
    CVTTSS2SI.addform('0xf3', '0100 11XB', '0x0f 0x2c', '11 reg r/m')
    CVTTSS2SI.addform('0xf3', '0100 0RXB', '0x0f 0x2c', 'mod reg r/m')
    CVTTSS2SI.addform('0xf3', '0100 10XB', '0x0f 0x2c', 'mod reg r/m', set(['100']))
    CVTTSS2SI.addform('0xf3', '0100 11XB', '0x0f 0x2c', 'mod reg r/m')

# ANDPS
ANDPS = Instruction("andps")
# 32-bit
if True:
    ANDPS.addform(None, None, '0x0f 0x54', '11 xmm1 xmm2')
    ANDPS.addform(None, None, '0x0f 0x54', 'mod xmm1 r/m')

# 64-bit
if True:
    ANDPS.addform(None, '0100 WRXB', '0x0f 0x54', '11 xmm1 xmm2')
    ANDPS.addform(None, '0100 WRXB', '0x0f 0x54', 'mod xmm1 r/m')

# ORPS
ORPS = Instruction("orps")
# 32-bit
if True:
    ORPS.addform(None, None, '0x0f 0x56', '11 xmm1 xmm2')
    ORPS.addform(None, None, '0x0f 0x56', 'mod xmm1 r/m')

# 64-bit
if True:
    ORPS.addform(None, '0100 WRXB', '0x0f 0x56', '11 xmm1 xmm2')
    ORPS.addform(None, '0100 WRXB', '0x0f 0x56', 'mod xmm1 r/m')

# XORPS
XORPS = Instruction("xorps")
# 32-bit
if True:
    XORPS.addform(None, None, '0x0f 0x57', '11 xmm1 xmm2')
    XORPS.addform(None, None, '0x0f 0x57', 'mod xmm1 r/m')

# 64-bit
if True:
    XORPS.addform(None, '0100 WRXB', '0x0f 0x57', '11 xmm1 xmm2')
    XORPS.addform(None, '0100 WRXB', '0x0f 0x57', 'mod xmm1 r/m')

# ADDPS
ADDPS = Instruction("addps")
# 32-bit
if True:
    ADDPS.addform(None, None, '0x0f 0x58', '11 xmm1 xmm2')
    ADDPS.addform(None, None, '0x0f 0x58', 'mod xmm1 r/m')

# 64-bit
if True:
    ADDPS.addform(None, '0100 WRXB', '0x0f 0x58', '11 xmm1 xmm2')
    ADDPS.addform(None, '0100 WRXB', '0x0f 0x58', 'mod xmm1 r/m')

# SUBPS
SUBPS = Instruction("subps")
# 32-bit
if True:
    SUBPS.addform(None, None, '0x0f 0x5c', '11 xmm1 xmm2')
    SUBPS.addform(None, None, '0x0f 0x5c', 'mod xmm1 r/m')

# 64-bit
if True:
    SUBPS.addform(None, '0100 WRXB', '0x0f 0x5c', '11 xmm1 xmm2')
    SUBPS.addform(None, '0100 WRXB', '0x0f 0x5c', 'mod xmm1 r/m')

# MULPS
MULPS = Instruction("mulps")
# 32-bit
if True:
    MULPS.addform(None, None, '0x0f 0x59', '11 xmm1 xmm2')
    MULPS.addform(None, None, '0x0f 0x59', 'mod xmm1 r/m')

# 64-bit
if True:
    MULPS.addform(None, '0100 WRXB', '0x0f 0x59', '11 xmm1 xmm2')
    MULPS.addform(None, '0100 WRXB', '0x0f 0x59', 'mod xmm1 r/m')

# DIVPS
DIVPS = Instruction("divps")
# 32-bit
if True:
    DIVPS.addform(None, None, '0x0f 0x5e', '11 xmm1 xmm2')
    DIVPS.addform(None, None, '0x0f 0x5e', 'mod xmm1 r/m')

# 64-bit
if True:
    DIVPS.addform(None, '0100 WRXB', '0x0f 0x5e', '11 xmm1 xmm2')
    DIVPS.addform(None, '0100 WRXB', '0x0f 0x5e', 'mod xmm1 r/m')

# MOVMSKPS
MOVMSKPS = Instruction("movmskps")
# 32-bit
if True:
    MOVMSKPS.addform(None, None, '0x0f 0x50', '11 xmm reg')

# 64-bit
if True:
    MOVMSKPS.addform(None, '0100 WRXB', '0x0f 0x50', '11 xmm reg')

# MOVD
MOVD = Instruction("movd")
# 32-bit
if True:
    MOVD.addform(OSIZE, None, '0x0f 0x6e', '11 xmm reg')
    MOVD.addform(OSIZE, None, '0x0f 0x7e', '11 xmm reg')

# 64-bit
if True:
    MOVD.addform(OSIZE, '0100 WRXB', '0x0f 0x6e', '11 xmm reg')
    MOVD.addform(OSIZE, '0100 WRXB', '0x0f 0x7e', '11 xmm reg', set(), set(['100']))

# MOVSD
MOVSD = Instruction("movsd")
# 32-bit
if True:
    MOVSD.addform('0xf2', None, '0x0f 0x10', '11 xmm1 xmm2')
    MOVSD.addform('0xf2', None, '0x0f 0x10', 'mod xmm r/m')
    MOVSD.addform('0xf2', None, '0x0f 0x11', '11 xmm1 xmm2')
    MOVSD.addform('0x67 0xf2', None, '0x0f 0x11', 'mod xmm r/m')

# 64-bit
if True:
    MOVSD.addform('0xf2', '0100 WRXB', '0x0f 0x10', '11 xmm1 xmm2')
    MOVSD.addform('0xf2', '0100 WRXB', '0x0f 0x10', 'mod xmm r/m')
    MOVSD.addform('0xf2', '0100 WRXB', '0x0f 0x11', '11 xmm1 xmm2')
    MOVSD.addform('0x67 0xf2', '0100 WRXB', '0x0f 0x11', 'mod xmm r/m')

# MOVDQA
MOVDQA = Instruction("movdqa")
# 32-bit
if True:
    MOVDQA.addform(OSIZE, None, '0x0f 0x6f', '11 xmm1 xmm2')
    MOVDQA.addform(OSIZE, None, '0x0f 0x6f', 'mod xmm r/m')
    MOVDQA.addform(OSIZE, None, '0x0f 0x7f', '11 xmm2 xmm1')
    MOVDQA.addform(SBXOSIZE, None, '0x0f 0x7f', 'mod xmm r/m')

# 64-bit
if True:
    MOVDQA.addform(OSIZE, '0100 WRXB', '0x0f 0x6f', '11 xmm1 xmm2')
    MOVDQA.addform(OSIZE, '0100 WRXB', '0x0f 0x6f', 'mod xmm r/m')
    MOVDQA.addform(OSIZE, '0100 WRXB', '0x0f 0x7f', '11 xmm2 xmm1')
    MOVDQA.addform(SBXOSIZE, '0100 WRXB', '0x0f 0x7f', 'mod xmm r/m')

# MOVDQU
MOVDQU = Instruction("movdqu")
# 32-bit
if True:
    MOVDQU.addform('0xf3', None, '0x0f 0x6f', '11 xmm1 xmm2')
    MOVDQU.addform('0xf3', None, '0x0f 0x6f', 'mod xmm r/m')
    MOVDQU.addform('0xf3', None, '0x0f 0x7f', '11 xmm2 xmm1')
    MOVDQU.addform('0x67 0xf3', None, '0x0f 0x7f', 'mod xmm r/m')

# 64-bit
if True:
    MOVDQU.addform('0xf3', '0100 WRXB', '0x0f 0x6f', '11 xmm1 xmm2')
    MOVDQU.addform('0xf3', '0100 WRXB', '0x0f 0x6f', 'mod xmm r/m')
    MOVDQU.addform('0xf3', '0100 WRXB', '0x0f 0x7f', '11 xmm2 xmm1')
    MOVDQU.addform('0x67 0xf3', '0100 WRXB', '0x0f 0x7f', 'mod xmm r/m')

# MOVAPD
MOVAPD = Instruction("movapd")
# 32-bit
if True:
    MOVAPD.addform(OSIZE, None, '0x0f 0x28', '11 xmm2 xmm1')
    MOVAPD.addform(OSIZE, None, '0x0f 0x29', '11 xmm1 xmm2')

# 64-bit
if True:
    MOVAPD.addform(OSIZE, '0100 WRXB', '0x0f 0x28', '11 xmm2 xmm1')
    MOVAPD.addform(OSIZE, '0100 WRXB', '0x0f 0x29', '11 xmm1 xmm2')

# PSLLQ
PSLLQ = Instruction("psllq")
# 32-bit
if True:
    PSLLQ.addform(None, None, '0x0f 0x73', '11 110 r/m', set(), set(), 8)
    PSLLQ.addform(OSIZE, None, '0x0f 0x73', '11 110 r/m', set(), set(), 8)

# 64-bit
if True:
    PSLLQ.addform(OSIZE, '0100 WRXB', '0x0f 0x73', '11 110 r/m', set(), set(), 8)

# CVTTSD2SI
CVTTSD2SI = Instruction("cvttsd2si")
# 32-bit
if True:
    CVTTSD2SI.addform('0xf2', None, '0x0f 0x2c', '11 reg1 reg2')
    CVTTSD2SI.addform('0xf2', None, '0x0f 0x2c', 'mod reg r/m')

# 64-bit
if True:
    CVTTSD2SI.addform('0xf2', '0100 WXRB', '0x0f 0x2c', '11 reg1 reg2', set(['100']))
    CVTTSD2SI.addform('0xf2', '0100 WXRB', '0x0f 0x2c', 'mod reg r/m', set(['100']))

# CVTSI2SD
CVTSI2SD = Instruction("cvtsi2sd")
# 32-bit
if True:
    CVTSI2SD.addform('0xf2', None, '0x0f 0x2a', '11 reg1 reg2')
    CVTSI2SD.addform('0xf2', None, '0x0f 0x2a', 'mod reg r/m')

# 64-bit
if True:
    CVTSI2SD.addform('0xf2', '0100 WXRB', '0x0f 0x2a', '11 reg1 reg2')
    CVTSI2SD.addform('0xf2', '0100 WXRB', '0x0f 0x2a', 'mod reg r/m')

# CVTSS2SD
CVTSS2SD = Instruction("cvtss2sd")
# 32-bit
if True:
    CVTSS2SD.addform('0xf3', None, '0x0f 0x5a', '11 reg1 reg2')

# 64-bit
if True:
    CVTSS2SD.addform('0xf3', '0100 WRXB', '0x0f 0x5a', '11 reg1 reg2')

# CVTSD2SS
CVTSD2SS = Instruction("cvtsd2ss")
# 32-bit
if True:
    CVTSD2SS.addform('0xf2', None, '0x0f 0x5a', '11 reg1 reg2')

# 64-bit
if True:
    CVTSD2SS.addform('0xf2', '0100 WRXB', '0x0f 0x5a', '11 reg1 reg2')

# CVTSD2SI
CVTSD2SI = Instruction("cvtsd2si")
# 32-bit
if True:
    CVTSD2SI.addform('0xf2', None, '0x0f 0x2d', '11 reg1 reg2')

# 64-bit
if True:
    CVTSD2SI.addform('0xf2', '0100 WRXB', '0x0f 0x2d', '11 reg1 reg2', set(['100']))

# Addsd
ADDSD = Instruction("addsd")
# 32-bit
if True:
    ADDSD.addform('0xf2', None, '0x0f 0x58', '11 reg1 reg2')
    ADDSD.addform('0xf2', None, '0x0f 0x58', 'mod reg r/m')

# 64-bit
if True:
    ADDSD.addform('0xf2', '0100 WXRB', '0x0f 0x58', '11 reg1 reg2')
    ADDSD.addform('0xf2', '0100 WXRB', '0x0f 0x58', 'mod reg r/m')    

# Subsd
SUBSD = Instruction("subsd")
# 32-bit
if True:
    SUBSD.addform('0xf2', None, '0x0f 0x5c', '11 reg1 reg2')

# 64-bit
if True:
    SUBSD.addform('0xf2', '0100 WXRB', '0x0f 0x5c', '11 reg1 reg2')

# Mulsd
MULSD = Instruction("mulsd")
# 32-bit
if True:
    MULSD.addform('0xf2', None, '0x0f 0x59', '11 reg1 reg2')
    MULSD.addform('0xf2', None, '0x0f 0x59', 'mod reg r/m')

# 64-bit
if True:
    MULSD.addform('0xf2', '0100 WXRB', '0x0f 0x59', '11 reg1 reg2')
    MULSD.addform('0xf2', '0100 WXRB', '0x0f 0x59', 'mod reg r/m')    

# Divsd
DIVSD = Instruction("divsd")
# 32-bit
if True:
    DIVSD.addform('0xf2', None, '0x0f 0x5e', '11 reg1 reg2')

# 64-bit
if True:
    DIVSD.addform('0xf2', '0100 WXRB', '0x0f 0x5e', '11 reg1 reg2')

# Andpd
ANDPD = Instruction("andpd")
# 32-bit
if True:
    ANDPD.addform(OSIZE, None, '0x0f 0x54', '11 reg1 reg2')

# 64-bit
if True:
    ANDPD.addform(OSIZE, '0100 WXRB', '0x0f 0x54', '11 reg1 reg2')

# Orpd
ORPD = Instruction("orpd")
# 32-bit
if True:
    ORPD.addform(OSIZE, None, '0x0f 0x56', '11 reg1 reg2')

# 64-bit
if True:
    ORPD.addform(OSIZE, '0100 WXRB', '0x0f 0x56', '11 reg1 reg2')

# Xorpd
XORPD = Instruction("xorpd")
# 32-bit
if True:
    XORPD.addform(OSIZE, None, '0x0f 0x57', '11 reg1 reg2')

# 64-bit
if True:
    XORPD.addform(OSIZE, '0100 WXRB', '0x0f 0x57', '11 reg1 reg2')

# Sqrtsd
SQRTSD = Instruction("sqrtsd")
# 32-bit
if True:
    SQRTSD.addform('0xf2', None, '0x0f 0x51', '11 reg1 reg2')
    SQRTSD.addform('0xf2', None, '0x0f 0x51', 'mod reg r/m')

# 64-bit
if True:
    SQRTSD.addform('0xf2', '0100 WRXB', '0x0f 0x51', '11 reg1 reg2')
    SQRTSD.addform('0xf2', '0100 WRXB', '0x0f 0x51', 'mod reg r/m')

# Ucomisd
UCOMISD = Instruction("ucomisd")
# 32-bit
if True:
    UCOMISD.addform(OSIZE, None, '0x0f 0x2e', '11 reg1 reg2')
    UCOMISD.addform(OSIZE, None, '0x0f 0x2e', 'mod reg r/m')

# 64-bit
if True:
    UCOMISD.addform(OSIZE, '0100 WRXB', '0x0f 0x2e', '11 reg1 reg2')
    UCOMISD.addform(OSIZE, '0100 WRXB', '0x0f 0x2e', 'mod reg r/m')

# Cmpsd
CMPSD = Instruction("cmpsd")
# 32-bit
if True:
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x0')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x1')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x2')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x3')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x4')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x5')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x6')
    CMPSD.addform('0xf2', None, '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x7')

# 64-bit
if True:
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x0')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x1')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x2')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x3')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x4')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x5')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x6')
    CMPSD.addform('0xf2', '0100 WRXB', '0x0f 0xc2', '11 reg1 reg2', set(), set(), 0, '0x7')

# Movmskpd
MOVMSKPD = Instruction("movmskpd")
# 32-bit
if True:
    MOVMSKPD.addform(OSIZE, None, '0x0f 0x50', '11 reg32 xmmreg')

# 64-bit
if True:
    MOVMSKPD.addform(OSIZE, '0100 WRXB', '0x0f 0x50', '11 reg32 xmmreg')

# ROUNDSD
ROUNDSD = Instruction("roundsd")
# 32-bit
if True:
    ROUNDSD.addform(OSIZE, None, '0x0f 0x3a 0x0b', '11 xmmreg reg', set(), set(), 8)

# 64-bit
if True:
    ROUNDSD.addform(OSIZE, '0100 WRXB', '0x0f 0x3a 0x0b', '11 xmmreg reg', set(), set(), 8)

# Extractps
EXTRACTPS = Instruction("extractps")
# 32-bit
if True:
    # reg from xmmreg , imm8
    EXTRACTPS.addform(OSIZE, None, '0x0f 0x3a 0x17', '11 xmmreg reg', set(), set(), 8)

# 64-bit
if True:
    # reg from xmmreg , imm8
    EXTRACTPS.addform(OSIZE, '0100 WRXB', '0x0f 0x3a 0x17', '11 xmmreg reg', set(), set(), 8)

# Fabs
FABS = Instruction("fabs")
if True:
    FABS.addform(None, None, '0xd9 0xe1')

# Fchs
FCHS = Instruction("fchs")
if True:
    FABS.addform(None, None, '0xd9 0xe0')

# Fmul
FMUL = Instruction("fmul")
if True:
    FMUL.addform(None, None, '0xdc 0xc8')
    FMUL.addform(None, None, '0xdc 0xc9')
    FMUL.addform(None, None, '0xdc 0xca')
    FMUL.addform(None, None, '0xdc 0xcb')
    FMUL.addform(None, None, '0xdc 0xcc')
    FMUL.addform(None, None, '0xdc 0xcd')
    FMUL.addform(None, None, '0xdc 0xce')
    FMUL.addform(None, None, '0xdc 0xcf')

# Fsub
FSUB = Instruction("fsub")
if True:
    # fsub
    FSUB.addform(None, None, '0xdc 0xe8')
    FSUB.addform(None, None, '0xdc 0xe9')
    FSUB.addform(None, None, '0xdc 0xea')
    FSUB.addform(None, None, '0xdc 0xeb')
    FSUB.addform(None, None, '0xdc 0xec')
    FSUB.addform(None, None, '0xdc 0xed')
    FSUB.addform(None, None, '0xdc 0xee')
    FSUB.addform(None, None, '0xdc 0xef')
    # fisub_s
    FSUB.addform(None, None, '0xda', 'mod 100 r/m')

# Fadd
FADD = Instruction("fadd")
if True:
    FADD.addform(None, None, '0xdc 0xc0')
    FADD.addform(None, None, '0xdc 0xc1')
    FADD.addform(None, None, '0xdc 0xc2')
    FADD.addform(None, None, '0xdc 0xc3')
    FADD.addform(None, None, '0xdc 0xc4')
    FADD.addform(None, None, '0xdc 0xc5')
    FADD.addform(None, None, '0xdc 0xc6')
    FADD.addform(None, None, '0xdc 0xc7')

# Faddp
FADDP = Instruction("faddp")
if True:
    FADDP.addform(None, None, '0xde 0xc0')
    FADDP.addform(None, None, '0xde 0xc1')
    FADDP.addform(None, None, '0xde 0xc2')
    FADDP.addform(None, None, '0xde 0xc3')
    FADDP.addform(None, None, '0xde 0xc4')
    FADDP.addform(None, None, '0xde 0xc5')
    FADDP.addform(None, None, '0xde 0xc6')
    FADDP.addform(None, None, '0xde 0xc7')

# Fsubp
FSUBP = Instruction("fsubp")
if True:
    FSUBP.addform(None, None, '0xde 0xe8')
    FSUBP.addform(None, None, '0xde 0xe9')
    FSUBP.addform(None, None, '0xde 0xea')
    FSUBP.addform(None, None, '0xde 0xeb')
    FSUBP.addform(None, None, '0xde 0xec')
    FSUBP.addform(None, None, '0xde 0xed')
    FSUBP.addform(None, None, '0xde 0xee')
    FSUBP.addform(None, None, '0xde 0xef')

# Fsubrp
FSUBRP = Instruction("fsubrp")
if True:
    FSUBRP.addform(None, None, '0xde 0xe0')
    FSUBRP.addform(None, None, '0xde 0xe1')
    FSUBRP.addform(None, None, '0xde 0xe2')
    FSUBRP.addform(None, None, '0xde 0xe3')
    FSUBRP.addform(None, None, '0xde 0xe4')
    FSUBRP.addform(None, None, '0xde 0xe5')
    FSUBRP.addform(None, None, '0xde 0xe6')
    FSUBRP.addform(None, None, '0xde 0xe7')

# Fmulp
FMULP = Instruction("fmulp")
if True:
    FMULP.addform(None, None, '0xde 0xc8')
    FMULP.addform(None, None, '0xde 0xc9')
    FMULP.addform(None, None, '0xde 0xca')
    FMULP.addform(None, None, '0xde 0xcb')
    FMULP.addform(None, None, '0xde 0xcc')
    FMULP.addform(None, None, '0xde 0xcd')
    FMULP.addform(None, None, '0xde 0xce')
    FMULP.addform(None, None, '0xde 0xcf')

# Fdiv
FDIV = Instruction("fdiv")
if True:
    FDIV.addform(None, None, '0xdc 0xf8')
    FDIV.addform(None, None, '0xdc 0xf9')
    FDIV.addform(None, None, '0xdc 0xfa')
    FDIV.addform(None, None, '0xdc 0xfb')
    FDIV.addform(None, None, '0xdc 0xfc')
    FDIV.addform(None, None, '0xdc 0xfd')
    FDIV.addform(None, None, '0xdc 0xfe')
    FDIV.addform(None, None, '0xdc 0xff')

# Fdivp
FDIVP = Instruction("fdivp")
if True:
    FDIVP.addform(None, None, '0xde 0xf8')
    FDIVP.addform(None, None, '0xde 0xf9')
    FDIVP.addform(None, None, '0xde 0xfa')
    FDIVP.addform(None, None, '0xde 0xfb')
    FDIVP.addform(None, None, '0xde 0xfc')
    FDIVP.addform(None, None, '0xde 0xfd')
    FDIVP.addform(None, None, '0xde 0xfe')
    FDIVP.addform(None, None, '0xde 0xff')

# Fprem
FPREM = Instruction("fprem")
if True:
    FPREM.addform(None, None, '0xd9 0xf8')

# Fprem1
FPREM1 = Instruction("fprem1")
if True:
    FPREM1.addform(None, None, '0xd9 0xf5')

# Fxch
FXCH = Instruction("fxch")
if True:
    FXCH.addform(None, None, '0xd9 0xc8')
    FXCH.addform(None, None, '0xd9 0xc9')
    FXCH.addform(None, None, '0xd9 0xca')
    FXCH.addform(None, None, '0xd9 0xcb')
    FXCH.addform(None, None, '0xd9 0xcc')
    FXCH.addform(None, None, '0xd9 0xcd')
    FXCH.addform(None, None, '0xd9 0xce')
    FXCH.addform(None, None, '0xd9 0xcf')

# Fincstp
FINCSTP = Instruction("fincstp")
if True:
    FINCSTP.addform(None, None, '0xd9 0xf7')

# Ffree
FFREE = Instruction("ffree")
if True:
    FFREE.addform(None, None, '0xdd 0xc0')
    FFREE.addform(None, None, '0xdd 0xc1')
    FFREE.addform(None, None, '0xdd 0xc2')
    FFREE.addform(None, None, '0xdd 0xc3')
    FFREE.addform(None, None, '0xdd 0xc4')
    FFREE.addform(None, None, '0xdd 0xc5')
    FFREE.addform(None, None, '0xdd 0xc6')
    FFREE.addform(None, None, '0xdd 0xc7')

# Ftst
FTST = Instruction("ftst")
if True:
    FTST.addform(None, None, '0xd9 0xe4')

# Fucomp
FUCOMP = Instruction("fucomp")
if True:
    FUCOMP.addform(None, None, '0xdd 0xe8')
    FUCOMP.addform(None, None, '0xdd 0xe9')
    FUCOMP.addform(None, None, '0xdd 0xea')
    FUCOMP.addform(None, None, '0xdd 0xeb')
    FUCOMP.addform(None, None, '0xdd 0xec')
    FUCOMP.addform(None, None, '0xdd 0xed')
    FUCOMP.addform(None, None, '0xdd 0xee')
    FUCOMP.addform(None, None, '0xdd 0xef')
# Fucompp
FUCOMPP = Instruction("fucompp")
if True:
    FUCOMPP.addform(None, None, '0xda 0xe9')

# Fucomi
FUCOMI = Instruction("fucomi")
if True:
    FUCOMI.addform(None, None, '0xdb 0xf0')
    FUCOMI.addform(None, None, '0xdb 0xf1')
    FUCOMI.addform(None, None, '0xdb 0xf2')
    FUCOMI.addform(None, None, '0xdb 0xf3')
    FUCOMI.addform(None, None, '0xdb 0xf4')
    FUCOMI.addform(None, None, '0xdb 0xf5')
    FUCOMI.addform(None, None, '0xdb 0xf6')
    FUCOMI.addform(None, None, '0xdb 0xf7')

# Fucomip
FUCOMIP = Instruction("fucomip")
if True:
    FUCOMIP.addform(None, None, '0xdf 0xe8')
    FUCOMIP.addform(None, None, '0xdf 0xe9')
    FUCOMIP.addform(None, None, '0xdf 0xea')
    FUCOMIP.addform(None, None, '0xdf 0xeb')
    FUCOMIP.addform(None, None, '0xdf 0xec')
    FUCOMIP.addform(None, None, '0xdf 0xed')
    FUCOMIP.addform(None, None, '0xdf 0xee')
    FUCOMIP.addform(None, None, '0xdf 0xef')

# Fcompp
FCOMPP = Instruction("fcompp")
if True:
    FCOMPP.addform(None, None, '0xde 0xd9')

# Fnstsw
FNSTSW = Instruction("fnstsw")
if True:
    FNSTSW.addform(None, None, '0xdf 0xe0')

# Fwait
FWAIT = Instruction("fwait")
if True:
    FWAIT.addform(None, None, '0x9b')

# Fnclex
FNCLEX = Instruction("fnclex")
if True:
    FNCLEX.addform(None, None, '0xdb 0xe2')

# Fsin
FSIN = Instruction("fsin")
if True:
    FSIN.addform(None, None, '0xd9 0xfe')

# Fcos
FCOS = Instruction("fcos")
if True:
    FCOS.addform(None, None, '0xd9 0xff')

# Fptan
FPTAN = Instruction("fptan")
if True:
    FPTAN.addform(None, None, '0xd9 0xf2')

# Fyl2x
FYL2X = Instruction("fyl2x")
if True:
    FYL2X.addform(None, None, '0xd9 0xf1')

# F2xm1
F2XM1 = Instruction("f2xm1")
if True:
    F2XM1.addform(None, None, '0xd9 0xf0')

# Fscale
FSCALE = Instruction("fscale")
if True:
    FSCALE.addform(None, None, '0xd9 0xfd')

# Fninit
FNINIT = Instruction("fninit")
if True:
    FNINIT.addform(None, None, '0xdb 0xe3')

# Frndint
FRNDINT = Instruction("frndint")
if True:
    FRNDINT.addform(None, None, '0xd9 0xfc')

# Sahf
SAHF = Instruction("sahf")
if True:
    SAHF.addform(None, None, '0x9e')

# Fldx
FLDX = Instruction("fldx")
if True:
    # fld1
    FLDX.addform(None, None, '0xd9 0xe8')
    # fldl2t
    FLDX.addform(None, None, '0xd9 0xe9')
    # fldl2e
    FLDX.addform(None, None, '0xd9 0xea')
    # fldpi
    FLDX.addform(None, None, '0xd9 0xeb')
    # fldlg2
    FLDX.addform(None, None, '0xd9 0xec')
    # fldln2
    FLDX.addform(None, None, '0xd9 0xed')
    # fldz
    FLDX.addform(None, None, '0xd9 0xee')

# Fld
FLD = Instruction("fld")
# 32-bit
if True:
    FLD.addform(None, None, '0xd9', 'mod 000 r/m')
    FLD.addform(None, None, '0xdd', 'mod 000 r/m')
    FLD.addform(None, None, '0xd9 0xc0')
    FLD.addform(None, None, '0xd9 0xc1')
    FLD.addform(None, None, '0xd9 0xc2')
    FLD.addform(None, None, '0xd9 0xc3')
    FLD.addform(None, None, '0xd9 0xc4')
    FLD.addform(None, None, '0xd9 0xc5')
    FLD.addform(None, None, '0xd9 0xc6')
    FLD.addform(None, None, '0xd9 0xc7')

# 64-bit
if True:
    FLD.addform(None, '0100 WRXB', '0xd9', 'mod 000 r/m')
    FLD.addform(None, '0100 WRXB', '0xdd', 'mod 000 r/m')

# Fstp
FSTP = Instruction("fstp")
# 32-bit
if True:
    FSTP.addform(SBX, None, '0xd9', 'mod 010 r/m')
    FSTP.addform(SBX, None, '0xdd', 'mod 010 r/m')
    FSTP.addform(SBX, None, '0xd9', 'mod 011 r/m')
    FSTP.addform(SBX, None, '0xdd', 'mod 011 r/m')
    FSTP.addform(None, None, '0xdd 0xd0')
    FSTP.addform(None, None, '0xdd 0xd1')
    FSTP.addform(None, None, '0xdd 0xd2')
    FSTP.addform(None, None, '0xdd 0xd3')
    FSTP.addform(None, None, '0xdd 0xd4')
    FSTP.addform(None, None, '0xdd 0xd5')
    FSTP.addform(None, None, '0xdd 0xd6')
    FSTP.addform(None, None, '0xdd 0xd7')
    FSTP.addform(None, None, '0xdd 0xd8')
    FSTP.addform(None, None, '0xdd 0xd9')
    FSTP.addform(None, None, '0xdd 0xda')
    FSTP.addform(None, None, '0xdd 0xdb')
    FSTP.addform(None, None, '0xdd 0xdc')
    FSTP.addform(None, None, '0xdd 0xdd')
    FSTP.addform(None, None, '0xdd 0xde')
    FSTP.addform(None, None, '0xdd 0xdf')    

# 64-bit
if True:
    FSTP.addform(SBX, '0100 WRXB', '0xd9', 'mod 010 r/m')
    FSTP.addform(SBX, '0100 WRXB', '0xdd', 'mod 010 r/m')
    FSTP.addform(SBX, '0100 WRXB', '0xd9', 'mod 011 r/m')
    FSTP.addform(SBX, '0100 WRXB', '0xdd', 'mod 011 r/m')

# Fild
FILD = Instruction("fild")
# 32-bit
if True:
    FILD.addform(None, None, '0xdf', 'mod 000 r/m')
    FILD.addform(None, None, '0xdb', 'mod 000 r/m')
    FILD.addform(None, None, '0xdf', 'mod 101 r/m')

# 64-bit
if True:
    FILD.addform(None, '0100 WRXB', '0xdf', 'mod 000 r/m')
    FILD.addform(None, '0100 WRXB', '0xdb', 'mod 000 r/m')
    FILD.addform(None, '0100 WRXB', '0xdf', 'mod 101 r/m')

# Fist
FIST = Instruction("fist")
# 32-bit
if True:
    FIST.addform(SBX, None, '0xdf', 'mod 010 r/m')
    FIST.addform(SBX, None, '0xdb', 'mod 010 r/m')
    FIST.addform(SBX, None, '0xdf', 'mod 011 r/m')
    FIST.addform(SBX, None, '0xdb', 'mod 011 r/m')
    FIST.addform(SBX, None, '0xdf', 'mod 111 r/m')

# 64-bit
if True:
    FIST.addform(SBX, '0100 WRXB', '0xdf', 'mod 010 r/m')
    FIST.addform(SBX, '0100 WRXB', '0xdb', 'mod 010 r/m')
    FIST.addform(SBX, '0100 WRXB', '0xdf', 'mod 011 r/m')
    FIST.addform(SBX, '0100 WRXB', '0xdb', 'mod 011 r/m')
    FIST.addform(SBX, '0100 WRXB', '0xdf', 'mod 111 r/m')

# Direct jmp rel1
JMP1 = Instruction("jmp", "jmp_rel1")
if True:
    JMP1.addform(None, None, '0xeb', None, set(), set(), 8)

# Direct jmp rel4
JMP4 = Instruction("jmp", "jmp_rel4")
if True:
    JMP4.addform(None, None, '0xe9', None, set(), set(), 32)

# Jcc rel1
Jcc1 = Instruction("jcc", "jcc_rel1")
if True:
    Jcc1.addform(None, None, '0111 tnnn', None, set(), set(), 8, None, True)
# Jcc rel4
Jcc4 = Instruction("jcc", "jcc_rel4")
if True:
    Jcc4.addform(None, None, '0000 1111 1000 tnnn', None, set(), set(), 32, None, True)

# Direct call
CALL = Instruction("call", "dcall")
if True:
    CALL.addform(None, None, '0xe8', None, set(), set(), 32)

ID = '0xf4'
JNEN3 = '0x2e 0x75 0xfd'

# Indirect jmp
IJMP = Instruction("ijmp", "ijmp")
if True:
    MOVL = [x + y for x in ['0x45 0x89 ', '0x45 0x8b ']
            for y in ['0xc0', '0xc9', '0xd2', '0xdb', '0xe4', '0xed', '0xf6', '0xff']]
    CMPB = ['0x65 0x41 0x80 ' + x + ' ' + ID
            for x in ['0x38', '0x39', '0x3a', '0x3b', '0x3c 0x24', '0x7d 0x00', '0x3e', '0x3f']]
    JMPR = ['0x41 0xff 0xe' + x
            for x in ['0', '1', '2', '3', '4', '5', '6', '7']]
    for i in range(8):
        for movl in MOVL:
            IJMP.addform(None, None, '%s %s %s %s' % (movl, CMPB[i], JNEN3, JMPR[i]))

    MOVL = [x + y for x in ['0x89 ', '0x8b ']
            for y in ['0xc0', '0xc9', '0xd2', '0xdb', '0xe4', '0xed', '0xf6', '0xff']]
    CMPB = ['0x65 0x80 ' + x + ' ' + ID
            for x in ['0x38', '0x39', '0x3a', '0x3b', '0x3c 0x24', '0x7d 0x00', '0x3e', '0x3f']]
    JMPR = ['0xff 0xe' + x
            for x in ['0', '1', '2', '3', '4', '5', '6', '7']]
    for i in range(8):
        for movl in MOVL:
            IJMP.addform(None, None, '%s %s %s %s' % (movl, CMPB[i], JNEN3, JMPR[i]))

# Indirect call
ICALL = Instruction("icall", "icall")
if True:
    MOVL = [x + y for x in ['0x45 0x89 ', '0x45 0x8b ']
            for y in ['0xc0', '0xc9', '0xd2', '0xdb', '0xe4', '0xed', '0xf6', '0xff']]
    CMPB = ['0x65 0x41 0x80 ' + x + ' ' + ID
            for x in ['0x38', '0x39', '0x3a', '0x3b', '0x3c 0x24', '0x7d 0x00', '0x3e', '0x3f']]
    CALLR = ['0x41 0xff 0xd' + x
            for x in ['0', '1', '2', '3', '4', '5', '6', '7']]
    for i in range(8):
        for movl in MOVL:
            ICALL.addform(None, None, '%s %s %s %s' % (movl, CMPB[i], JNEN3, CALLR[i]))

    MOVL = [x + y for x in ['0x89 ', '0x8b ']
            for y in ['0xc0', '0xc9', '0xd2', '0xdb', '0xe4', '0xed', '0xf6', '0xff']]
    CMPB = ['0x65 0x80 ' + x + ' ' + ID
            for x in ['0x38', '0x39', '0x3a', '0x3b', '0x3c 0x24', '0x7d 0x00', '0x3e', '0x3f']]
    CALLR = ['0xff 0xd' + x
            for x in ['0', '1', '2', '3', '4', '5', '6', '7']]
    for i in range(8):
        for movl in MOVL:
            ICALL.addform(None, None, '%s %s %s %s' % (movl, CMPB[i], JNEN3, CALLR[i]))

JNECHECK = ['0x0f 0x85 ' + Imm32(), '0x75 ' + Imm8()]
ALIGNNOP = ['', '0x90', '0x66 0x90', '0x0f 0x1f 0x00', '0x0f 0x1f 0x40 0x00',
            '0x0f 0x1f 0x44 0x00 0x00', '0x66 0x0f 0x1f 0x44 0x00 0x00',
            '0x0f 0x1f 0x80 0x00 0x00 0x00 0x00']
# MCFI call
MCFICALL = Instruction("mcficall", "mcficall")
if True:
    MOVL = [y + x for x in ['0xc0', '0xdb'] for y in ['0x89 ', '0x8b ']]
    # the bid slot will be filled by later calls
    MOVBID = '0x65 0x4c 0x8b 0x14 0x25 0x00 0x00 0x00 0x00'
    CMPQ = ['0x65 0x4c 0x39 ' + x for x in ['0x10', '0x13']] # rax and rbx
    CALLR = ['0xff 0xd0', '0xff 0xd3'] # only rax and rbx
    for i in range(len(CALLR)):
        for j in range(len(MOVL)):
            for k in range(len(ALIGNNOP)):
                for jnecheck in JNECHECK:
                    MCFICALL.addform(None, None,
                                     '%s %s %s %s %s %s' %
                                     (MOVL[j], MOVBID, CMPQ[i], jnecheck, ALIGNNOP[k], CALLR[i]))

# MCFI check
MCFICHECK = Instruction("mcficheck", "mcficheck")
if True:
    MOVTID = ['0x65 0x4c 0x8b 0x18', '0x65 0x4c 0x8b 0x1b'] # movq %gs:(%ra/bx), %r10
    TESTB = '0x41 0xf6 0xc3 0x01'
    JEHLTNETRY = [('0x74 0x09', JNECHECK[0]), ('0x74 0x05', JNECHECK[1])]
    CMPL = ['0x45 0x39 0xd3', '0x45 0x3b 0xd3']
    HLT = '0xf4'
    for movtid in MOVTID:
        for cmpl in CMPL:
            for (jehlt, jnetry) in JEHLTNETRY:
                MCFICHECK.addform(None, None,
                                  '%s %s %s %s %s %s' %
                                  (movtid, TESTB, jehlt, cmpl, jnetry, HLT))

# MCFI ret
MCFIRET = Instruction("mcfiret", "mcfiret")
if True:
    MOVL = ['0x89 0xc9', '0x8b 0xc9'] # movl %ecx, %ecx
    # the bid slot will be filled by later calls
    MOVBID = '0x65 0x48 0x8b 0x3c 0x25 0x00 0x00 0x00 0x00'
    MOVTID = '0x65 0x48 0x8b 0x31'
    CMPQ = ['0x48 0x39 0xfe', '0x48 0x8b 0xfe']
    JNECHECK = '0x75 0x02'
    JMPR = '0xff 0xe1'
    TESTB = '0x40 0xf6 0xc6 0x01'
    JEHLT = '0x74 0x04'
    CMPL = ['0x39 0xfe', '0x3b 0xfe']
    JNETRY = '0x75 0xe1'
    HLT = '0xf4'
    for movl in MOVL:
        for cmpq in CMPQ:
            for cmpl in CMPL:
                MCFIRET.addform(None, None, '%s %s %s %s %s %s %s %s %s %s %s' %
                                (movl, MOVBID, MOVTID, cmpq, JNECHECK, JMPR, TESTB,
                                 JEHLT, cmpl, JNETRY, HLT))
