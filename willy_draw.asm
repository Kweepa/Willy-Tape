DrawPlayerEntry
    lda dead
    bne +
    jsr CheckRoomEdge   ; return C=1 if should not draw Willy (transitioning)
    bcc +
    rts
+

DrawPlayerBody
    lda willy_hidden
    beq +
    rts
+
	; clear overlaps/touches
	ldx #(48+6-1)
	lda #0
-
	sta player_overlap,x
	dex
	bpl -

    ; first read screen bitmaps to player bitmaps
    ldx px
    ldy py
    jsr ConvertXYToScreenAddr
    lda #<player_udg
    sta play_udg
    lda #>player_udg
    sta play_udg+1

	ldx #0
-
    ldy draw_player_offsets,x
    ; screen chr -> UDG ptr (inlined setudgadd)
    lda #0
    sta tmp
    lda (scr_ptr),y
    sta player_overlap,x
    inx
    asl
    asl
    rol tmp
    asl
    rol tmp
    sta udg_ptr
    lda #>udg_base
    adc tmp
    sta udg_ptr+1
    ; copy 8 bytes into player UDG slot (inlined copy_udg)
    ldy #7
--
    lda (udg_ptr),y
    sta (play_udg),y
    dey
    bpl --

    lda play_udg
    clc
    adc #8
    sta play_udg

	cpx #6
	bne -

    ; now or player bitmaps to player udg 3x2
    lda px
    and #$03
    sta tmp
    lda lastxmove
    bpl +
    lda tmp
    clc
    adc #4
    sta tmp
+
    lda tmp
    jsr GetPlayerFrameAddr
    lda arr
    clc
    adc #16
    sta arr2
    lda arr+1
    adc #0
    sta arr2+1

    lda py
    and #$07
    tax

    ldy #0
draw_center_loop
    lda (arr),y
	and player_udg,x
	sta player_touch,x
    lda (arr),y
    ora player_udg,x
    sta player_udg,x

    lda (arr2),y
	and player_udg+24,x
	sta player_touch+24,x
    lda (arr2),y
    ora player_udg+24,x
    sta player_udg+24,x
    inx
    iny
    cpy #16
    bne draw_center_loop

	ldx #5
-
	lda draw_player_chrs,x
	ldy draw_player_offsets,x
	sta (scr_ptr),y
	dex
	bpl -

coll_check
	; now check for collisions
	ldy #5
	ldx #(6*8-1)
--
	lda #0
	sta tmp
-
	lda tmp
	ora player_touch,x
	sta tmp
	dex
	txa
	and #7
    cmp #7
	bne -
	lda tmp
	beq +
	lda player_overlap,y
	jsr HandleOverlapChar
+
	dey
	bpl --
    +BorderDebugColor (WHITE + 8)
draw_player_done
    rts

check_for_pickup

; HandleOverlapChar - A = screen chr under a Willy cell (player_overlap).
; Items: pickup. Hazards/guardians: kill. Solids: pass through.
; coll_check only calls us when player_touch is non-zero.
; this function should preserve x and y
HandleOverlapChar
    cmp #ITEM_CHR
    bne ++

    ; pickup item at overlap cell (inlined PickupItemAtOverlap)
    txa
    pha
    ldx map
    lda pickup_got,x
    bne +
    inc pickup_got,x
    inc items_collected
    jsr item_erase

    ; play item pickup sound
    lda #240
    sta $900c
    lda #10
    sta $900e
+
    pla
    tax
    rts

++
    cmp #TILE_HAZARD + TILE_CHR_BASE
    beq kill_player
    cmp #TILE_SOLID + TILE_CHR_BASE
    beq dont_kill_player
    cmp #GUARDIAN_CHR
    bcs +
    rts

+

    ; hit a guardian (22-33) or rope UDG (34+). Guardians kill directly;
    ; rope UDGs attach only when meta_content_room_has_rope (no pha — kill_player must
    ; not return with an extra byte on the stack).
    cmp #ROPE_FIRST_UDG
    bcc kill_player
    lda meta_content_room_has_rope
    beq kill_player
    jmp rope_attach ; tail call

kill_player
    lda #1
    sta dead
dont_kill_player
    rts

draw_player_offsets
    !byte 24, 48, 72, 25, 49, 73                    ; DrawPlayer
draw_player_chrs
    !byte PLAY_CHR, PLAY_CHR+1, PLAY_CHR+2, PLAY_CHR+3, PLAY_CHR+4, PLAY_CHR+5
