; Per-room item erase stub — 11 bytes in meta tail @ meta_content_item_erase.
; CLI: -DCOL_ADDR=... -DMAP_ADDR=... -DEMPTY_COLOR=... -DSLOT_BYTES=11

!source "equates.asm"

*= $0000
item_erase
    lda #EMPTY_COLOR
    sta COL_ADDR
    lda #TILE_EMPTY
    sta MAP_ADDR
    rts

!if * <> SLOT_BYTES {
    !error "item_erase size ", *, " != SLOT_BYTES ", SLOT_BYTES
}
