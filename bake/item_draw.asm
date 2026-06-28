; Per-room item draw stub — 11 bytes in meta tail @ meta_content_item_draw.
; CLI: -DSCR_ADDR=... -DMAP_ADDR=... -DITEM_CHR=... -DTILE_ITEM=... -DSLOT_BYTES=11
; Colour: FlickerItem @ image_base (not here).

!source "equates.asm"

*= $0000
item_draw
    lda #ITEM_CHR
    sta SCR_ADDR
    lda #TILE_ITEM
    sta MAP_ADDR
    rts

!if * <> SLOT_BYTES {
    !error "item_draw size ", *, " != SLOT_BYTES ", SLOT_BYTES
}
