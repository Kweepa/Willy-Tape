; rope implementation - takes about 110 scan lines for rope_draw

; willy grabs the rope the same way he collides with other items, by checking the UDG while drawing
; so in this case, we'd detect a collision, then use the rope_segment_y table to match willy's y with a segment
; then if holding the rope, move willy to the coordinates of that segment

!zone rope_implementation

; ===========================================================================

rope_clear_pre_player_draw

; clear the rope UDGs from the screen memory
; no need to clear color as we're using white for both the rope and the player
    lda rope_udg
    beq +
    asl
    tax

    lda #TILE_CHR_BASE ; empty tile
-
    sta (rope_old_screen_pos,x) ; valid 6502, intended for tables of addresses in ZP
    dex
    dex
    bpl -
+
    rts

; ===========================================================================

rope_draw

; first clear the old rope

    lda #0
    ldx #ROPE_UDG_BYTES - 1
-
    sta ROPE_FIRST_UDG_ADDRESS,x
    dex
    bpl -

; then advance the rope frame
; we need the index to go from 0 to 53, then back to 0 for a right swing
; then from 0 to 53, and back to 0 for a left swing (with rope_xadd interpreted as negative)
; rope_swing_dir determines this

    ldx rope_frame
    inx
    lda rope_swing_dir
    bpl +
    dex
    dex
+
    stx rope_frame
    beq .rope_flip_dir
    cpx #53
    bne .rope_frame_done
    lda rope_swing_side
    eor #1
    sta rope_swing_side
.rope_flip_dir
    lda rope_swing_dir
    eor #$fe // special case that flips -1 <> 1
    sta rope_swing_dir
.rope_frame_done


; now step through the rope segments and draw them

; rope_udg starts at 0
; rope_scr starts at ROPE_ANCHOR_SCR (y=0, x=ROPE_ANCHOR_COL)
; rope_bit starts at $80

    ; since we're starting with the first UDG,
    ; fill in the first entry in the old_screen table immediately at the anchor cell
    lda #<ROPE_ANCHOR_SCR
    sta rope_scr
    sta rope_old_screen_pos
    lda #>ROPE_ANCHOR_SCR
    sta rope_scr+1
    sta rope_old_screen_pos+1
    ; write the first actual rope UDG to the screen
    ldy #0
    lda #ROPE_FIRST_UDG
    sta (rope_scr),y
    lda #$80
    sta rope_bit
    lda #0
    sta rope_y
    sta rope_udg
    sta rope_loop_count
    ; write address of first rope UDG in charset RAM
    lda #<ROPE_FIRST_UDG_ADDRESS
    sta rope_udg_mem
    lda #>ROPE_FIRST_UDG_ADDRESS
    sta rope_udg_mem+1

    ; anchor: col 12 = 96 VIC px; row 0 = py 3 (where the first dot is drawn)
    lda #96
    sta rope_segment_cur_x
    lda #3
    sta rope_segment_cur_y

    ; calculate loop count to stop storing segment x,y
    lda #32
    sta rope_seg_skip_above
    lda rope_willy_is_holding
    beq +
    ldx rope_willy_seg
    inx
    stx rope_seg_skip_above
+

    ; loop rope_frame..rope_frame+31 backwards; rope_loop_count = segment 0..31 (0=anchor, 31=tip)
    lda rope_frame
    clc
    adc #31
    sta rope_index

rope_loop_top
    lda #0
    sta rope_udg_advance

    ; shift rope_bit by xadd in an x loop
    ldx rope_index
    cpx #ROPE_XADD_BYTES ; 0 implied after the end of the table
    bpl .xadd_skip
    lda rope_xadd,x
    !if ROPE_TEST {
    sta debug_x_step
    }
    beq .xadd_skip
    tax
.xshift_side
    ldy rope_swing_side
    beq .xshift_left
.xshift_right
    lda rope_loop_count
    cmp rope_seg_skip_above
    bcs .xshift_right_rot
    dec rope_segment_cur_x
.xshift_right_rot
    asl rope_bit
    bcc .xadd_loop_tail
    rol rope_bit
    lda #1
    sta rope_udg_advance
    dec rope_scr
    bne .xadd_loop_tail
    dec rope_scr+1
    bne .xadd_loop_tail
.xshift_left
    lda rope_loop_count
    cmp rope_seg_skip_above
    bcs .xshift_left_rot
    inc rope_segment_cur_x
.xshift_left_rot
    lsr rope_bit
    bcc .xadd_loop_tail
    ror rope_bit
    lda #1
    sta rope_udg_advance
    inc rope_scr
    bne .xadd_loop_tail
    inc rope_scr+1
.xadd_loop_tail
    dex
    bne .xshift_side

.xadd_skip
    ; now shift down Y (same value added to rope_y and rope_segment_cur_y when tracking)
    lda #3
    ldx rope_index
    cpx #32
    bpl .y_step_ready
    lda #2
.y_step_ready
    tax                    ; step preserved in x
    !if ROPE_TEST {
    stx debug_y_step
    }

    lda rope_loop_count
    cmp rope_seg_skip_above
    bcs .y_track_done
    txa
    clc
    adc rope_segment_cur_y
    sta rope_segment_cur_y
.y_track_done
    txa
    clc
    adc rope_y
    sta rope_y
    cmp #8
    bmi .y_no_wrap
    eor #8 ; set to 0 (rope_y wrapped -> next char row)
    sta rope_y
    lda rope_scr
    clc
    adc #24
    sta rope_scr
    lda rope_scr+1
    adc #0
    sta rope_scr+1
    ldx #1
    stx rope_udg_advance
.y_no_wrap

    lda rope_udg_advance
    beq .udg_write_done
    inc rope_udg
    lda rope_udg
    clc
    adc #ROPE_FIRST_UDG
    ldy #0
    sta (rope_scr),y
    lda rope_udg
    asl
    tax
    lda rope_scr
    sta rope_old_screen_pos,x
    lda rope_scr+1
    sta rope_old_screen_pos+1,x
    lda rope_udg_mem
    clc
    adc #8
    sta rope_udg_mem
.udg_write_done
    lda rope_bit
    ldy rope_y
    sta (rope_udg_mem),y

    lda rope_loop_count
    cmp rope_seg_skip_above
    bcs .seg_y_done
    tax
    lda rope_segment_cur_y
    sta ROPE_SEGMENT_Y,x
.seg_y_done

    inc rope_loop_count
    !if ROPE_TEST {
    jsr rope_test_loop_hook
    }
    lda rope_index
    cmp rope_frame
    beq .rope_loop_done
    dec rope_index
    jmp rope_loop_top
.rope_loop_done

    ; snap willy to attach point
    lda rope_willy_is_holding
    beq ++
    lda rope_segment_cur_x
    lsr
    sec
    sbc #2
    sta px
    lda rope_segment_cur_y
    sec
    sbc #8
    bpl +
    ldy meta_content_conn       ; north @conn — same gate as willy.asm jump-above
    bpl +
    lda #0                      ; clamp: sealed north or not at anchor
+
    sta py

++
    rts
