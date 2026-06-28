PlayInGameMusic

	; stop last frame's sound effects (moved from gameloop to decrease body of gameloop)
	; also reset volume to 10 since jump may have changed it
	lda #0
	jsr play_sound_at_default_volume

	; toggle music on a key
	; ADGJL row ($FB): toggle music on rising edge only.
	; music_key_prev holds last frame's scan mask (0 = released).
	; rising = (old ^ scan) & scan — nonzero iff a key went down this frame.
	ldx #$fb
	jsr ScanKeyRow
	ldy music_key_prev
	sta music_key_prev
	tya
	eor music_key_prev
	and music_key_prev
	beq +
	lda music_enabled
	eor #$ff
	sta music_enabled
+

	; always update the note
	lda music_index
	and #$3f
	sta music_index
	tax
	lda INGAME_TUNE_SEQ,x
	and #$0f
	tay
	lda ingame_tune_pitch,y
	and music_enabled
	sta $900b

	; advance the counters
	inc music_delay
	lda music_delay
	and #7
	sta music_delay
	bne +
	inc music_index
+
	rts

