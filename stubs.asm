; Optional debug helpers — not called by the game. Link at end of PRG for size accounting.
; To use: jsr ramp_dbg_hud from calculate_ramp_y (or elsewhere) after assembling with stubs.asm included.

ramp_dbg_hud
    lda was_on_ground
    clc
    adc #$b0
    sta hud_dbg_scr+0
    lda is_on_ramp
    clc
    adc #$b0
    sta hud_dbg_scr+1
    lda is_in_ramp_bounds
    clc
    adc #$b0
    sta hud_dbg_scr+2
    lda was_on_ground
    bne dbg_falling_0
    lda inairtime
    cmp #27
    bcc dbg_falling_0
    lda #1
    bne dbg_falling_store
dbg_falling_0
    lda #0
dbg_falling_store
    clc
    adc #$b0
    sta hud_dbg_scr+3
    lda ramp_y
    ldy #$b0
-
    cmp #100
    bcc +
    sbc #100
    iny
    bne -
+
    sty hud_dbg_scr+5
    ldy #$b0
-
    cmp #10
    bcc ++
    sbc #10
    iny
    bne -
++
    sty hud_dbg_scr+6
    clc
    adc #$b0
    sta hud_dbg_scr+7
    rts

hud_dbg_scr = screen_base + hud_row_off + 15   ; cols 15-21 on HUD row
