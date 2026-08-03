# ============================================================
# Unity BinaryWriter
# ============================================================
def write7bit_int(f, value: int):
    while value >= 0x80:
        f.write(bytes([(value & 0x7F) | 0x80]))
        value >>= 7
    f.write(bytes([value]))
def write_string(f, text: str):
    encoded = text.encode("utf-8")
    write7bit_int(f, len(encoded))
    f.write(encoded)