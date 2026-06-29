;
; LoadRoom — decompress catalogue room to screen + colour/map RAM.
;

room_lfn = 15

room_name
    !text "R00"

LoadRoom
    lda #0
    sta $900b
    sta $900c

    jsr SetColors
    jsr FormatRoomName

    lda map
    cmp #ROOM_TITLE
    beq LoadRoomDone

    jsr FindRoomRecord
    bcc LoadRoomBlank

    jsr DecompressRoom
    jsr TapePaintMap
    rts

LoadRoomBlank
    jsr TapeClearScreen
    jsr TapeInitMeta
    jsr ApplyBorderFromMeta
    jsr TapePaintRoomColors
    jsr TapePaintMap
LoadRoomDone
    rts

LoadRoomFile
    jmp LoadRoom

; Parse catalogue record at stream_ptr -> screen_base, meta.
DecompressRoom
    jsr TapeInitMeta
    jsr ReadTitlePtr
    jsr SkipTitle
    jsr ParseMeta8
    jsr ApplyBorderFromMeta
    jsr ApplySpawnFromMeta
    jsr ReadTileColors
    jsr LoadRoomUdgs
    jsr RleUnpack
    jsr ApplyRoomOverlays
    jsr PaintPickup
    jsr StampHudRow
    jsr LoadRoomGuardians
    rts

ApplyBorderFromMeta
    lda meta_content_border
    sta $900f
    rts

ApplySpawnFromMeta
    lda use_room_spawn
    beq +
    lda meta_content_spawn_px
    sta px
    lda meta_content_spawn_py
    sta py
+
    rts

ParseMeta8
    ldy #0
    lda (stream_ptr),y
    sta meta_content_conn
    iny
    lda (stream_ptr),y
    sta meta_content_conn+1
    iny
    lda (stream_ptr),y
    sta meta_content_conn+2
    iny
    lda (stream_ptr),y
    sta meta_content_conn+3
    iny
    lda (stream_ptr),y
    sta meta_content_spawn_px
    iny
    lda (stream_ptr),y
    sta meta_content_spawn_py
    iny
    lda (stream_ptr),y
    sta meta_content_record_flags
    iny
    lda (stream_ptr),y
    sta meta_content_border
    lda #8
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

ReadTileColors
    ldy #0
-
    lda (stream_ptr),y
    sta tile_color_src,y
    iny
    cpy #6
    bne -
    lda stream_ptr
    clc
    adc #6
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

ReadTitlePtr
    lda stream_ptr
    sta title_ptr
    lda stream_ptr_hi
    sta title_ptr+1
    rts

SkipTitle
-
    ldy #0
    lda (stream_ptr),y
    beq title_done
    inc stream_ptr
    bne -
    inc stream_ptr_hi
    jmp -
title_done
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    rts

ApplyRoomOverlays
    ldy #0
    lda (stream_ptr),y
    sta ramp_tmp                  ; pickup offset lo
    iny
    lda (stream_ptr),y
    sta ramp_y                    ; pickup offset hi
    lda ramp_tmp
    cmp #$ff
    bne fix_pickup_addr
    lda ramp_y
    cmp #$ff
    beq pickup_addr_done
fix_pickup_addr
    lda ramp_tmp
    clc
    adc #<screen_base
    sta ramp_tmp
    lda ramp_y
    adc #>screen_base
    sta ramp_y
pickup_addr_done
    jsr Skip2

    lda meta_content_record_flags
    and #FLAG_RAMP
    beq +
    jsr ApplyRamp3
+
    lda meta_content_record_flags
    and #FLAG_CONVEYOR
    beq +
    jsr ApplyConveyor3
+
    rts

PaintPickup
    lda ramp_y
    cmp #$ff
    bne paint_pickup
    lda ramp_tmp
    cmp #$ff
    beq paint_pickup_done
paint_pickup
    lda ramp_tmp
    sta arr
    lda ramp_y
    sta arr+1
    lda #ITEM_CHR
    ldy #0
    sta (arr),y
    lda arr
    sta col_ptr
    lda arr+1
    clc
    adc #>(color_base - screen_base)
    sta col_ptr+1
    lda tile_color_src + TILE_ITEM
    sta (col_ptr),y
paint_pickup_done
    rts

Skip3
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    rts

Skip2
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    rts

StampHudRow
    ldy #0
    ldx #0
-
    cpy #18
    beq stamp_icons
    lda (title_ptr),y
    beq pad_title
    pha
    jsr ToUpper
    jsr AsciiToScreen
    sta screen_base+hud_row_off,x
    pla
    iny
    inx
    jmp -
pad_title
    lda #160
    sta screen_base+hud_row_off,x
    inx
    iny
    jmp -
stamp_icons
    lda #MEN_CHR
    sta hud_men_scr
    lda #HUD_ITEM_CHR
    sta hud_item_scr
    rts

LoadRoomUdgs
    ldx #7
    lda #0
-
    sta udg_base,x              ; chr 0 empty — always zero, not in catalogue
    dex
    bpl -

    lda #TILE_PLATFORM          ; floor chr 1
    jsr LoadOneUdgChr
    lda #TILE_SOLID             ; wall chr 2
    jsr LoadOneUdgChr
    lda #ITEM_CHR               ; pickup chr 6
    jsr LoadOneUdgChr

    lda meta_content_record_flags
    and #FLAG_NASTY
    beq +
    lda #TILE_HAZARD
    jsr LoadOneUdgChr
+
    lda meta_content_record_flags
    and #FLAG_RAMP
    beq +
    lda #TILE_RAMP
    jsr LoadOneUdgChr
+
    lda meta_content_record_flags
    and #FLAG_CONVEYOR
    beq +
    lda #TILE_CONVEYOR
    jsr LoadOneUdgChr
+
    jsr EnsureVicCharset
    rts

; Keep $9005 charset block at $1800 after UDG writes.
EnsureVicCharset
    lda #$ce
    sta $9005
    rts

; A = VIC chr. Copy 8 bytes from stream_ptr to udg_base + chr*8.
LoadOneUdgChr
    asl
    asl
    asl
    clc
    adc #<udg_base
    sta udg_ptr
    lda #>udg_base
    adc #0
    sta udg_ptr+1
    ldy #0
-
    lda (stream_ptr),y
    sta (udg_ptr),y
    iny
    cpy #8
    bne -
    lda #8
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

LoadRoomGuardians
    lda meta_content_record_flags
    and #FLAG_ARROW
    beq +
    lda #5
    jsr SkipBytes
+
    ldy #0
    lda (stream_ptr),y
    sta meta_content_guardians
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    lda meta_content_guardians
    beq guardians_done
    sta num
    lda #0
    sta guardian_index

load_guardian_loop
    ldy #0
    lda (stream_ptr),y
    sta hx
    iny
    lda (stream_ptr),y
    sta hy
    iny
    lda (stream_ptr),y
    sta hl
    iny
    lda (stream_ptr),y
    sta hr
    iny
    lda (stream_ptr),y
    sta hd
    iny
    lda (stream_ptr),y
    sta hc
    iny
    lda (stream_ptr),y
    sta guard_axis
    iny
    lda (stream_ptr),y
    sta mov                     ; set_idx

    jsr LookupGuardianSet

    lda #0
    sta g_frame
    jsr WriteGuardianRuntimeRecord

    lda #8
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    inc guardian_index
    dec num
    bne load_guardian_loop

guardians_done
    rts

; mov = set_idx -> ht = pool frame start, g_fctl from set metadata.
LookupGuardianSet
    lda mov
    asl
    tax
    lda guardian_set_metadata,x
    sta ht
    lda guardian_set_metadata+1,x
    sta ts
    lda guard_axis
    bne lookup_guardian_set_v
    lda ts
    cmp #8
    beq lookup_guardian_set_bidir
    lda #0
    sta g_fctl
    rts
lookup_guardian_set_bidir
    lda #1
    sta g_fctl
    rts
lookup_guardian_set_v
    lda ts
    sec
    sbc #1
    sta g_fctl
    rts

WriteGuardianRuntimeRecord
    jsr CalcGuardianRecPtr
    ldy #g_off_axis
-
    lda hx,y
    sta (arr),y
    dey
    bpl -
    rts

SkipBytes
    sta mov
    beq SkipBytesDone
SkipBytesLoop
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    dec mov
    bne SkipBytesLoop
SkipBytesDone
    rts

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

AsciiToScreen
    cmp #'A'
    bcc ats_other
    cmp #'Z'+1
    bcs ats_other
    sec
    sbc #'A'
    clc
    adc #129
    rts
ats_other
    cmp #'0'
    bcc ats_plain
    cmp #'9'+1
    bcs ats_plain
    clc
    adc #128
    rts
ats_plain
    clc
    adc #128
    rts

ToUpper
    cmp #'a'
    bcc +
    cmp #'z'+1
    bcs +
    sec
    sbc #$20
+
    rts
