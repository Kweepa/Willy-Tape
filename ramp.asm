; ===========================================================================
; call this once per frame, irrespective of movement
; ramp_y = feet Y on ramp surface; py is head (feet = py + 16).

calculate_ramp_y
    lda #0
    sta is_in_ramp_bounds
    lda px
    tax
    sec
    sbc meta_content_ramp_rx1
    tay
    bmi .exit_calc

    txa
    cmp meta_content_ramp_rx2
    bcs .exit_calc

    ; ramp_y = ry + ((2 * dx EOR E) + A)  — E/A baked per ramp type

    tya
    asl
    eor meta_content_ramp_E
    clc
    adc meta_content_ramp_A
    clc
    adc meta_content_ramp_ry
    sta ramp_y
    cmp meta_content_ramp_ymin
    bcs +
    lda meta_content_ramp_ymin
    sta ramp_y
+
    lda #1
    sta is_in_ramp_bounds

.exit_calc
    rts

; ===========================================================================
; Call when moving horizontally on the ground or on a ramp — snaps py to
; ramp_y - 16 when feet within +/-2 of ramp surface. Caller (CollideLeftRight)
; must gate on (was_on_ground OR is_on_ramp) and xadd != 0.

do_walking_ramp_check
    lda #0
    sta is_on_ramp
    lda is_in_ramp_bounds
    beq wr_out

    lda py
    clc
    adc #16
    sec
    sbc ramp_y
    bcc wr_below
    cmp #3
    bcc wr_snap
    bcs wr_out

wr_below:
    lda ramp_y
    sec
    sbc py
    sbc #16
    cmp #3
    bcs wr_out

wr_snap:
    lda ramp_y
    sec
    sbc #16
    sta py
    lda #1
    sta is_on_ramp

wr_out:
    rts

; ===========================================================================
; Call when falling straight down onto a ramp (not on ground, not already
; on ramp, no horizontal movement). Caller (collide_down) must gate on
; !on_ground, !is_on_ramp, and xadd == 0.

do_falling_ramp_check
    lda #0
    sta is_on_ramp
    lda is_in_ramp_bounds
    beq .fall_ramp_check_end

    lda last_py
    clc
    adc #13         ; 13 instead of 16 so that when changing rooms east/west on a ramp
    cmp ramp_y      ; we end up on the ramp in in the new room, not falling through it
    bcs .fall_ramp_check_end

    lda newy
    ; clc - we know carry is clear (see bcc above)
    adc #16
    cmp ramp_y
    bcc .fall_ramp_check_end

    lda ramp_y
    ; sec - we know carry is set (see bcs above)
    sbc #16
    sta py
    lda #1
    sta is_on_ramp
    jsr try_fall_death

.fall_ramp_check_end
    rts

