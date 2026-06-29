;
; LoadRoom — tape build (Phase 1): clear screen, default meta, paint colour/map.
; Phase 3 replaces body with catalogue decompress.
;

room_lfn = 15

room_name
    !text "R00"

LoadRoom
    lda #0
    sta $900b
    sta $900c

    jsr SetColors
    jsr TapeClearScreen
    jsr TapeInitMeta
    jsr FormatRoomName

    lda map
    cmp #ROOM_TITLE
    beq LoadRoomDone

    jsr TapePaintRoomColors
    jsr TapePaintMap

LoadRoomDone
    rts

LoadRoomFile
    ; Phase 6: cassette load entry
    jmp LoadRoom

TapeClearScreen
    lda #TILE_CHR_BASE + TILE_EMPTY
    ldx #0
-
    sta screen_base,x
    sta screen_base+$80,x
    inx
    bne -
    rts

TapeInitMeta
    ; Minimal defaults so DrawMap / edge checks do not read garbage
    lda #0
    ldx #0
-
    sta meta_content_src,x
    inx
    cpx #tail_size
    bne -

    lda #$ff
    sta meta_content_conn
    sta meta_content_conn+1
    sta meta_content_conn+2
    sta meta_content_conn+3
    lda #44
    sta meta_content_spawn_px
    lda #104
    sta meta_content_spawn_py
    lda #8
    sta meta_content_border
    rts

TapePaintRoomColors
    ldy #0
-
    lda screen_base,y
    and #$0f
    tax
    lda tile_color_src,x
    sta color_base,y

    lda screen_base+$80,y
    and #$0f
    tax
    lda tile_color_src,x
    sta color_base+$80,y

    iny
    bne -
    rts

TapePaintMap
    ldy #0
-
    lda screen_base,y
    sta map_base,y
    lda screen_base+$80,y
    sta map_base+$80,y
    iny
    bne -

    ldy #24
    lda #7
-
    sta color_base + 383,y
    dey
    bne -
    rts

FormatRoomName
    lda map
    ldy #'0'
-
    cmp #10
    bcc +
    sbc #10
    iny
    bne -
+
    adc #'0'
    sta room_name+2
    sty room_name+1
    rts
