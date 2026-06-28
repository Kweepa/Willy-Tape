; Per-room conveyor UDG animation — 19-byte prefix slot @ $1A15 (room_code_base).
; CLI: -DBELT=$ff|$01|$00 -DSLOT_BYTES=19

!source "equates.asm"

*= $0000
AnimateConveyors
    lda left_right_ctr
    bne +
!if BELT = $ff {
    lda conveyor_udg_lo
    asl
    rol conveyor_udg_lo
    lda conveyor_udg_hi
    lsr
    ror conveyor_udg_hi
}
!if BELT = 1 {
    lda conveyor_udg_lo
    lsr
    ror conveyor_udg_lo
    lda conveyor_udg_hi
    asl
    rol conveyor_udg_hi
}
+
    rts

!if * < SLOT_BYTES {
    !fill SLOT_BYTES - *, $ea
}
!if * > SLOT_BYTES {
    !error "AnimateConveyors size ", *, " exceeds SLOT_BYTES ", SLOT_BYTES
}
