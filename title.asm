; Title screen — propfont credits, wait for SPACE or FIRE release.
; Layout: 20-byte table (5×4) — tweak row/col/firstudg/colour/offset until happy.
; String blob: bake/title_strings.inc (tools/gen_title_strings.py).

!zone title

TitleScreen
    lda #10
    sta $900f
    lda #YEL
    jsr SetColors
    jsr ClearScreen
    jsr .draw_titles

.title_loop
    jsr WaitForRaster
    ldx #$ef                      ; space bar row
    jsr ScanKeyRow
    bne .title_exit_keyboard
    jsr .stick_fire_pressed
    bne .title_exit_fire
    jmp .title_loop

.title_exit_keyboard
    ldx #$ef
    jsr ScanKeyRow
    bne .title_exit_keyboard      ; wait for release
    rts

.title_exit_fire
    jsr .stick_fire_pressed
    bne .title_exit_fire          ; wait for release
    rts

; Z set = no fire, Z clear = fire pressed (bit 5 of $9111 active-low)
.stick_fire_pressed
    lda $9111
    and #$20
    eor #$20
    rts

.draw_titles
    lda #0
    sta .title_line_index
-
    jsr .draw_one_line
    inc .title_line_index
    lda .title_line_index
    cmp #4
    bne -
    rts

; Line index in .title_line_index (font routines clobber X/Y).
; also in A
.draw_one_line
    tax
    lda title_line_firstudg,x
    sta propfont_first
    jsr .stamp_propfont_row

    lda #<title_text
    sta arr
    lda #>title_text
    sta arr+1
    ldx .title_line_index
    lda title_line_text_offset,x
    clc
    adc arr
    sta arr
    bcc +
    inc arr+1
+
    jmp PrintSpecFontStringBody

.stamp_propfont_row
    ldx .title_line_index
    ldy title_line_y,x
    lda title_line_x,x
    tax
    jsr ConvertTileXYToScreenAddr

    ldx .title_line_index
    lda title_line_length,x
    sta .title_line_current_length
    lda title_line_firstudg,x

    ldy #0
-
    sta (scr_ptr),y
    clc
    adc #1
    iny
    cpy .title_line_current_length
    bne -
    rts

.title_line_index
    !byte 0
.title_line_current_length
    !byte 0

title_line_y
    !byte 4, 5, 8, 13
title_line_x
    !byte 7, 7, 6, 6
title_line_length
    !byte 10, 10, 12, 13
title_line_firstudg
    !byte 1, 16, 32, 48
title_line_text_offset
    !byte 0, 16, 30, 50

!source "bake/title_strings.inc"