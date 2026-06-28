; Per-room arrow bake — UDG @ chr 46, init + update @ chr 47+ ($1D78).
; CLI: -DCOOKED_X=... -DCOOKED_Y=... -DCOOKED_SOUND_X=... -DARROW_V=1|$ff
;      -DARROW_TILE=46 -DARROW_CODE_BYTES=88

!source "equates.asm"

ConvertXYToScreenAddr = $0392

*= $0000
arrow_init_bake
	lda #COOKED_X  ; <- compile time constant (got from room text file @arrow x=)
	sta arrow_x_zp
	rts

arrow_update_bake
	ldx left_right_ctr      ; every 4th frame (same cadence as conveyors / h-guardians)
	beq +
	rts
+
	ldy #COOKED_Y  ; ConvertXY Y for tile row (@arrow y >> 3), baked in mkroom
	jsr ConvertXYToScreenAddr

	ldy arrow_x_zp
	cpy #24
	bcs +

	; replace the tile
	lda (map_ptr),y
	and #$0f   ; mask out the random high nibble
	ora #$10   ; bump up to match the tile udgs
	sta (scr_ptr),y
+
	; increment and play sound
!if ARROW_V = 1 {
	iny ; or dey, depending on direction (compile time instruction @arrow v= -1 or 1)
}
!if ARROW_V <> 1 {
	dey ; or dey, depending on direction (compile time instruction @arrow v= -1 or 1)
}
	tya
	and #127
	tay
	sty arrow_x_zp
	cpy #COOKED_SOUND_X  ; <- compile time constant (@arrowsoundx)
	bne +
	lda #129
	sta $900c
	lda #10
	sta $900e
+
	cpy #24
	bcs +

	; draw
	lda #ARROW_TILE
	sta (scr_ptr),y
+
	rts

!if * > ARROW_CODE_BYTES {
	!error "arrow.asm size ", *, " exceeds ARROW_CODE_BYTES ", ARROW_CODE_BYTES
}
