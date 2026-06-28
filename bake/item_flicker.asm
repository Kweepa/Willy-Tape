; Per-room item colour flash — 16-byte slot @ image_base ($1A05).
; CLI: -DPICKUP_GOT=... -DCOL_ADDR=... -DSLOT_BYTES=16

!source "equates.asm"

*= $0000
FlickerItem
    lda PICKUP_GOT
    bne +
    ldx COL_ADDR
    inx
    txa
    and #7
    sta COL_ADDR
+
    rts

!if * < SLOT_BYTES {
    !fill SLOT_BYTES - *, $ea
}
!if * > SLOT_BYTES {
    !error "FlickerItem size ", *, " exceeds SLOT_BYTES ", SLOT_BYTES
}
