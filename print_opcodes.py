import hermes_dec.parsers.hbc_opcodes.hbc92 as h

for name in ['LoadConstString', 'LoadConstStringLongIndex', 'JStrictEqual', 'JStrictNotEqual', 'Jmp', 'PutById', 'GetById', 'GetByVal', 'PutByIdShort', 'PutNewOwnById', 'Mov', 'StrictEq', 'JmpTrue', 'JmpFalse']:
    cls = h._name_to_instruction[name]
    ops = [f'{getattr(o.operand_meaning, "name", "none")}:{o.operand_type.__name__}' for o in cls.operands]
    print(f'{cls.opcode:02x}: {name:25s} -> {ops}')
