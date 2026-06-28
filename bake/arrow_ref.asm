; Reference: bake/arrow.asm — init + update baked together @ chr 47+ ($1D78).
; Arrow UDG @ chr 46 ($1D70). No sprite frame 8.
;
; so in a room if there are these lines:
; @arrow y=<tile_y> x=<tile_x> v=[-1 or 1] sound=<value>
; @arrowudg N,N,N,N,N,N,N,N
; then place arrow UDG (8 bytes) at chr 46 and arrow code at chr 47+
; and set a byte in the metadata to indicate that there's an arrow in the room
;
; in game, just these
;
;   in LoadRoom
;		; 8 bytes
;		lda meta_content_has_arrow
;		beq +
;		jsr arrow_init
;	+
;
;	in gameloop, just after $900c <- 0
;		; 8 bytes
;		lda meta_content_has_arrow
;		beq +
;		jsr arrow_update
;	+
;
; so the run-time cost is 16 bytes
;

; =====================================

arrow_init
	lda #cooked_x_value  ; <- compile time constant (got from room text file @arrow x=)
	sta arrow_x_zp
	rts

; =====================================

arrow_update

	ldx left_right_ctr      ; every 4th frame (same cadence as conveyors / h-guardians)
	beq +
	rts
+
	; setup (x is 0 thanks to above check)
	ldy #COOKED_Y  ; ConvertXY Y for tile row (@arrow y >> 3), baked in mkroom
	jsr ConvertXYToScreenAddr

	ldy arrow_x_zp
	cpy #24
	bcs +

	; replace the tile
	lda (map_ptr),y
	and #$0f   ; mask out the random high nibble
	ora #$10   ; bump up into the tile udg range
	sta (scr_ptr),y
+
	; increment and play sound
	iny ; or dey, depending on direction (compile time instruction @arrow v= -1 or 1)
	tya
	and #127
	tay
	sty arrow_x_zp
	cpy #cooked_launch_sound_x  ; <- compile time constant (@arrowsoundx)
	bne +
	lda #129  ; low sound
	sta $900c
+
	cpy #24
	bcs +

	; draw
	lda #ARROW_TILE    ; see above, ARROW_TILE is 46
	sta (scr_ptr),y
+
	rts
