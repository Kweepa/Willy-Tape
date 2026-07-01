;
; LoadRoom — decompress catalogue room to screen + colour/map RAM.
;

LoadRoom
    lda #0
    sta $900b
    sta $900c

    jsr SetColors

    lda map
    cmp #ROOM_TITLE
    beq LoadRoomDone

    jsr FindRoomRecord
    jsr DecompressRoom
    jsr TapePaintMap
    jsr InitPlayerState

LoadRoomDone
    rts

InitPlayerState
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
    jsr ApplyBorderFromMeta
    jsr ApplySpawnFromMeta
    jsr ReadTileColors
    jsr LoadRoomUdgs
    jsr RleUnpack
    jsr ApplyRoomOverlays
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


; A = next catalogue byte; advances stream_ptr ($52-$53).
LoadByteFromStream
    ldy #0
    lda (stream_ptr),y
    php
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    plp
    rts

ParseMeta8
    jsr LoadByteFromStream
    sta meta_content_conn
    jsr LoadByteFromStream
    sta meta_content_conn+1
    jsr LoadByteFromStream
    sta meta_content_conn+2
    jsr LoadByteFromStream
    sta meta_content_conn+3
    jsr LoadByteFromStream
    sta meta_content_spawn_px
    jsr LoadByteFromStream
    sta meta_content_spawn_py
    jsr LoadByteFromStream
    sta meta_content_record_flags
    lda meta_content_record_flags
    and #FLAG_ROPE
    sta meta_content_room_has_rope
    lda meta_content_record_flags
    and #FLAG_ARROW
    sta meta_content_has_arrow
    jsr LoadByteFromStream
    sta meta_content_border
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
    sta title_ptr
    lda stream_ptr_hi
    sta title_ptr+1
-
    jsr LoadByteFromStream
    bne -

    lda title_ptr
    sta arr
    lda title_ptr+1
    sta arr+1
    ldy #0
    jmp PrintSpecFontString

ApplyRoomOverlays
    jsr LoadByteFromStream
    sta pickup_scr
    jsr LoadByteFromStream
    sta pickup_scr+1
    lda pickup_scr+1
    bmi pickup_col_done
    lda pickup_scr
    sta pickup_col
    lda pickup_scr+1
    clc
    adc #>(color_base - screen_base)
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
    ldx #7
    lda #0
-
    sta udg_base,x              ; chr 0 empty — always zero
    dex
    bpl -

    jsr LoadByteFromStream
    tax
    lda #<udg_pool_floor
    sta scr_ptr
    lda #>udg_pool_floor
    sta scr_ptr+1
    lda #TILE_PLATFORM
    jsr LoadUdgFromPool

    jsr LoadByteFromStream
    tax
    lda #<udg_pool_wall
    sta scr_ptr
    lda #>udg_pool_wall
    sta scr_ptr+1
    lda #TILE_SOLID
    jsr LoadUdgFromPool

    jsr LoadByteFromStream
    tax
    lda #<udg_pool_pickup
    sta scr_ptr
    lda #>udg_pool_pickup
    sta scr_ptr+1
    lda #ITEM_CHR
    jsr LoadUdgFromPool

    jsr LoadByteFromStream
    tax
    lda meta_content_record_flags
    and #FLAG_NASTY
    beq load_udg_skip_nasty
    lda #<udg_pool_nasty
    sta scr_ptr
    lda #>udg_pool_nasty
    sta scr_ptr+1
    lda #TILE_HAZARD
    jsr LoadUdgFromPool
load_udg_skip_nasty
    jsr LoadByteFromStream
    tax
    lda meta_content_record_flags
    and #FLAG_RAMP
    beq load_udg_skip_ramp
    lda #<udg_pool_ramp
    sta scr_ptr
    lda #>udg_pool_ramp
    sta scr_ptr+1
    lda #TILE_RAMP
    jsr LoadUdgFromPool
load_udg_skip_ramp
    jsr LoadByteFromStream
    tax
    lda meta_content_record_flags
    and #FLAG_CONVEYOR
    beq load_udg_skip_belt
    lda #<udg_pool_belt
    sta scr_ptr
    lda #>udg_pool_belt
    sta scr_ptr+1
    lda #TILE_CONVEYOR
    jsr LoadUdgFromPool
load_udg_skip_belt
    jsr EnsureVicCharset
    rts

; A = VIC chr, X = pool index, scr_ptr = pool type base (contiguous ZP $05-$06).
LoadUdgFromPool
    stx ramp_tmp
    pha
    lda ramp_tmp
    asl
    asl
    asl
    clc
    adc scr_ptr
    sta scr_ptr
    bcc +
    inc scr_ptr+1
+
    pla
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
    lda (scr_ptr),y
    sta (udg_ptr),y
    iny
    cpy #8
    bne -
    rts

EnsureVicCharset
    lda #$ce
    sta $9005
    rts

LoadRoomGuardians
    lda meta_content_record_flags
    and #FLAG_ARROW
    beq +
    lda #5
    jsr SkipBytes
+
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
