start_game
	jsr ResetGame

start_map
	jsr ResetMap
    jsr DrawMap
main_loop
    jsr ErasePlayer_EraseGuardians_UpdateMoveCounters
    lda meta_content_room_has_rope
    beq +
    jsr rope_pre_draw
+
    lda map
    cmp #ROOM_MASTER_BED
    bne +
    jsr master_bed_hook
+
    jsr MoveGuardians
    jsr GetPlayerInput
    ; stopping last frame's sound effects folded into PlayInGameMusic
    jsr PlayInGameMusic
    lda meta_content_has_arrow
    beq +
    jsr arrow_update
+
    jsr Collide
    jsr DrawHud
    jsr CheckEndingTeleport
    jsr FlickerItem             ; baked per room at image_base
    jsr AnimateConveyors
    jsr WaitForRaster
    +BorderDebugColor 8

    lda dead
    beq main_loop

    ; prevent infinite death loop
    lda safe_transition_count
    beq +
    sta fall_death_respawn
+
    ; reset volume (could have been jumping when we died)
    ; due to above, A=0 already. plus due to below, the note will be set again quickly
    jsr play_sound_at_default_volume

    ; death flash
    ldy #25
    lda #(WHITE + 8)
    ldx #0
-
    eor #(WHITE ^ RED)
    sta $900f
    pha
    txa
    eor #240
    tax
    stx $900c
    jsr WaitForRaster ; clobbers A
    pla
    dey
    bne -
 
    dec men
    ; inc men    ; make sure to not check this in enabled
    bne start_map
    beq start_game

ErasePlayer_EraseGuardians_UpdateMoveCounters

    ; erase player

    lda willy_hidden
    bne erase_player_done
    ldx px
    ldy py
    jsr ConvertXYToScreenAddr
	ldx #5
-
	ldy cell_off_2x3,x
	lda (map_ptr),y
	and #$0f
	cmp #TILE_ITEM
	bne +
	lda #ITEM_CHR
	sta (scr_ptr),y
	bne ++
+
	ora #$10
	sta (scr_ptr),y
++
	dex
	bpl -
erase_player_done

    ; erase guardians

    ldx meta_content_guardians
    beq .erase_guardians_done
    dex
    stx guardian_index

.erase_guardian_loop
    jsr CopyDownGuardianData
    ldx hx
    ldy hy
    jsr ConvertXYToScreenAddr
    ldx #3
    lda hy
    and #7
    beq +
    inx
    inx
+
    ; erase_block
-
    ldy cell_off_2x3,x
    lda #TILE_CHR_BASE
    sta (scr_ptr),y
    lda #WHITE
    sta (col_ptr),y
    dex
    bpl -

    dec guardian_index
    bpl .erase_guardian_loop

.erase_guardians_done

    ; update move counters

    lda rope_grab_cooldown
    beq +
    dec rope_grab_cooldown
+
    dec left_right_ctr
    bpl +
    lda #3
    sta left_right_ctr
+
	dec up_down_ctr
	bpl +
	lda #2
	sta up_down_ctr
+
    rts

