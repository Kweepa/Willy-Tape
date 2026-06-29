; ===========================================================================
; Called at end of ApplyRamp: hx=col_start, mov=row_start, num=length,
; arr3=3 (/) or 1 (\). Writes meta_content_ramp_*.

BakeRampMeta
    lda hx
    clc
    adc num
    sec
    sbc #1
    sta hc                  ; col_end

    ldx arr3
    cpx #3
    beq .br_up_right
    lda #RAMP_UP_LEFT
    sta meta_content_ramp
    lda #0
    sta meta_content_ramp_E
    sta meta_content_ramp_A
    jmp .br_bounds
.br_up_right
    lda #RAMP_UP_RIGHT
    sta meta_content_ramp
    lda #$ff
    sta meta_content_ramp_E
    lda #1
    sta meta_content_ramp_A

.br_bounds
    lda hx
    asl
    asl
    sec
    sbc #4
    sta meta_content_ramp_rx1
    lda hc
    asl
    asl
    clc
    adc #4
    sta meta_content_ramp_rx2

    lda meta_content_ramp_rx1
    jsr ramp_surface_abs
    ldx arr3
    cpx #3
    beq .br_store_ry
    sec
    sbc #4                  ; toe 6 minus UP_LEFT_RY_ADJUST 2
.br_store_ry
    sta meta_content_ramp_ry

    ldx arr3
    cpx #3
    bne .br_ymin_px
    lda hc
    asl
    asl
    jmp .br_ymin_surf
.br_ymin_px
    lda hx
    asl
    asl
.br_ymin_surf
    jsr ramp_surface_abs
    ldx arr3
    cpx #3
    beq .br_store_ymin
    sec
    sbc #6
.br_store_ymin
    sta meta_content_ramp_ymin
    rts

; A = px -> A = absolute feet Y on ramp surface (hx, mov, num, arr3).
ramp_surface_abs
    sta ramp_tmp
    lda num
    cmp #1
    beq .rsa_flat
    lda ramp_tmp
    clc
    adc #3
    sta arr2
    lda arr2
    lsr
    lsr
    sec
    sbc hx
    sta arr
    lda mov
    ldx arr3
    cpx #3
    bne .rsa_row_inc
    sec
    sbc arr
    jmp .rsa_row_done
.rsa_row_inc
    clc
    adc arr
    jmp .rsa_row_done
.rsa_flat
    lda ramp_tmp
    clc
    adc #3
    sta arr2
    lda mov
    jmp .rsa_row_done
.rsa_row_done
    asl
    asl
    asl
    sta arr
    lda arr2
    and #3
    asl
    ldx arr3
    cpx #3
    bne .rsa_yleft
    sta ramp_tmp
    lda #6
    sec
    sbc ramp_tmp
    jmp .rsa_finish
.rsa_yleft
.rsa_finish
    clc
    adc arr
    rts

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

