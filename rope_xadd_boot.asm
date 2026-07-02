; Rope horizontal shift table — copied to cassette buffer $0316 at WarmStart.
; Same bytes as tools/rope_table.py / original Spectrum rope table.

!zone rope_xadd_boot

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
!if boot_rope_xadd_size <> ROPE_XADD_BYTES {
!error "boot_rope_xadd_size must match ROPE_XADD_BYTES"
}

rope_xadd = ROPE_XADD
