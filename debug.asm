; Raster timing probes — toggle BORDER_DEBUG in defines.asm

!macro BorderDebugColor .byte {
!if BORDER_DEBUG {
    lda #.byte
    sta $900f
}
}

!macro BorderDebugGuardianIndex {
!if BORDER_DEBUG {
    lda #8
    clc
    adc guardian_index
    sta $900f
}
}
