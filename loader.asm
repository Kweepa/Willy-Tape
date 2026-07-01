;
; LoadRoom — decompress catalogue room to screen + colour/map RAM.
;

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
    rts

LoadRoomArrow
    lda meta_content_record_flags
    and #FLAG_ARROW
    beq LoadRoomArrowDone

    jsr LoadByteFromStream
    lsr
    lsr
    lsr
    clc
    adc #1
    asl
    asl
    asl
    sta arrow_row_y

    jsr LoadByteFromStream
    sta arrow_x_zp

    jsr LoadByteFromStream
    cmp #1
    beq arrow_is_rtl
    lda #0
    jmp arrow_rtl_done
arrow_is_rtl
    lda #1
arrow_rtl_done
    sta arrow_rtl

    jsr LoadByteFromStream
    sta arrow_sound_x

    jsr LoadByteFromStream

LoadRoomArrowDone
    rts

LoadRoomGuardians
    jsr LoadByteFromStream
    sta meta_content_guardians
    lda meta_content_guardians
    beq guardians_done
    sta num
    lda #0
    sta guardian_index

load_guardian_loop
    jsr LoadByteFromStream
    sta hx
    jsr LoadByteFromStream
    sta hy
    jsr LoadByteFromStream
    sta hl
    jsr LoadByteFromStream
    sta hr
    jsr LoadByteFromStream
    sta hd
    jsr LoadByteFromStream
    sta hc
    jsr LoadByteFromStream
    sta guard_axis
    jsr LoadByteFromStream
    sta mov                     ; set_idx

    jsr LookupGuardianSet

    lda #0
    sta g_frame
    jsr WriteGuardianRuntimeRecord

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

SkipBytes
    sta mov
    beq SkipBytesDone
-
    jsr LoadByteFromStream
    dec mov
    bne -
SkipBytesDone
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
    lda #$ff
    sta pickup_scr
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
