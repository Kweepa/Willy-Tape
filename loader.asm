;
; LoadRoom — decompress catalogue room to screen + colour/map RAM.
;

!zone loader

LoadRoom
    lda #0
    sta $900b
    sta $900c

    jsr SetColors

    jsr FindRoomRecord
    jsr DecompressRoom
    jsr TapePaintMap

    ; init player state

    ldx #0
    stx belt_active
    stx is_on_ramp
    stx rope_willy_is_holding
    stx rope_udg
    stx rope_frame
    stx rope_grab_cooldown
    stx rope_swing_side
    inx
    stx rope_swing_dir
    stx on_ground
    stx was_on_ground

    lda use_room_spawn
    beq +
    lda meta_content_spawn_px
    sta px
    lda meta_content_spawn_py
    sta py
+
    jsr calculate_ramp_y

    lda #27
    sta inairtime
    lda py
    sta last_py
    rts

; Parse catalogue record at stream_ptr -> screen_base, meta.
DecompressRoom
    jsr TapeInitMeta
    jsr ReadTitle
    jsr ParseMeta8
    jsr ApplySpawnFromMeta
    jsr ReadTileColors
    jsr LoadRoomUdgs
    jsr RleUnpack
    jsr ApplyRoomOverlays
    jsr StampHudRow
    jsr LoadRoomArrow
    jsr LoadRoomGuardians
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

ReadTileColors
    ldx #0
-
    jsr LoadByteFromStream
    sta tile_color_src,x
    inx
    cpx #6
    bne -
    rts

ReadTitle
    lda stream_ptr
    sta arr
    lda stream_ptr+1
    sta arr+1
    jsr PrintSpecFontString
-
    jsr LoadByteFromStream ; skip over null terminated string
    bne -
    rts

ApplyRoomOverlays
    jsr LoadByteFromStream
    sta pickup_scr
    sta pickup_col
    jsr LoadByteFromStream
    sta pickup_scr+1
    ora #$84 ; add $84 to get from $10 to $94
    sta pickup_col+1
pickup_col_done
    lda meta_content_record_flags
    and #FLAG_RAMP
    beq +
    jsr ApplyRamp
+
    lda meta_content_record_flags
    and #FLAG_CONVEYOR
    beq +
    jsr ApplyConveyor
+
    rts

StampHudRow
    lda #MEN_CHR
    sta hud_men_scr
    lda #HUD_ITEM_CHR
    sta hud_item_scr
    rts

LoadRoomUdgs
    lda meta_content_record_flags
    sta tmp
    ldx #1
-
    lsr tmp
    bcc +
    txa
    jsr LoadOneUdgChr
+
    inx
    cpx #7
    bne -
    rts

LoadRoomArrow
    lda meta_content_record_flags
    and #FLAG_ARROW
    beq +

    jsr LoadByteFromStream
    sta arrow_row_y

    and #1
    sta arrow_rtl
    tax
    lda arrow_start_x,x
    sta arrow_x_zp
    lda arrow_sound_tbl,x
    sta arrow_sound_x

+
    rts

arrow_start_x
    !byte ARROW_X_LTR, ARROW_X_RTL
arrow_sound_tbl
    !byte ARROW_SND_LTR, ARROW_SND_RTL

LoadRoomGuardians
    jsr LoadByteFromStream
    sta meta_content_guardians
    lda meta_content_guardians
    beq guardians_done
    sta num
    lda #0
    sta guardian_index

load_guardian_loop
    ldx #0
-
    jsr LoadByteFromStream
    ldy guardian_cat_zp,x
    sta $00,y
    inx
    cpx #8
    bne -

    jsr LookupGuardianSet

    lda #0
    sta g_frame
    jsr WriteGuardianRuntimeRecord

    inc guardian_index
    dec num
    bne load_guardian_loop

guardians_done
    rts

guardian_cat_zp
    !byte hx, hy, hl, hr, hd, hc, guard_axis, mov

; mov = set_idx -> ht = pool frame start, g_fctl from set metadata.
LookupGuardianSet
    lda mov
    asl
    tax
    lda sprite_set_metadata,x
    sta ht
    lda sprite_set_metadata+1,x
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

TapeInitMeta
    lda #0
    ldx #0
-
    sta meta_content_src,x
    inx
    cpx #tail_size
    bne -

    lda #$ff
    sta pickup_scr+1
    lda #RAMP_BOUNDS_NONE
    sta meta_content_ramp_rx1
    sta meta_content_ramp_rx2
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
