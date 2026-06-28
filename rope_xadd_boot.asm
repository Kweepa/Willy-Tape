; Rope horizontal shift table — copied to cassette buffer $35C at WarmStart.
; Same bytes as tools/rope_table.py / original Spectrum rope table.

boot_rope_xadd_pack
    !byte 1,2,3,2,2,2,3,1
    !byte 2,2,2,2,0,1,2,0
    !byte 1,2,1,1,1,2,1,2
    !byte 1,2,1,2,1,2,1,2
    !byte 1,2,1,2,1,2,1,2
    !byte 1,2,1,2,1,0,1,1
    !byte 1,1,1,0,1,1
boot_rope_xadd_pack_end = *

boot_rope_xadd_size = boot_rope_xadd_pack_end - boot_rope_xadd_pack
