;
; Proportional font — ported from Miner-main/font.asm.
; Title strings in catalogue use 1-based compact glyph bytes (0 = end; N = glyph N-1).
; fontchars table: bake/fontchars.asm (subset of tools/fontchars_full.asm).
; Composite canvas: UDG chr PROPFONT_CHR .. PROPFONT_CHR+PROPFONT_COLS-1.
;

!zone font

fontchars
        !source "bake/fontchars.asm"

; A = compact glyph index -> arr2 = fontchars + index*8
GetCharDefAddr
        ldx #0
        stx arr2+1
        asl
        rol arr2+1
        asl
        rol arr2+1
        asl
        rol arr2+1
        adc #<fontchars
        sta arr2
        lda arr2+1
        adc #>fontchars
        sta arr2+1
        rts

; A = glyph index -> width in pixels (min 4)
GetCharWidth
        jsr GetCharDefAddr
        ldy #7
        lda #0
-
        ora (arr2),y
        dey
        bpl -
        cmp #0
        beq +
        ldx #10                     ; include a blank pixel line
-
        dex
        lsr
        bcc -
        txa
        rts
+
        lda #4
        rts

; (arr) = 1-based glyph string; Y = start index -> stringwidth
GetStringWidth
        sty stringindex

        lda #0
        sta stringwidth
-
        ldy stringindex
        lda (arr),y
        beq +
        iny
        sty stringindex
        sec
        sbc #1
        jsr GetCharWidth
        clc
        adc stringwidth
        sta stringwidth
        bcc -
+
        lda stringwidth
        rts

PutFontUDGsOnScreen
        ; fill the characters with 255 (inverse video with eor below); 0 = normal video
        ldx #(PROPFONT_COLS * 8)
        lda #0
-
        sta propfont_udg-1,x
        dex
        bne -

        ; write em to the screen
        ldx #0
-
        txa
        clc
        adc #PROPFONT_CHR
        sta screen_base + hud_row_off,x
        lda #YELLOW
        sta color_base + hud_row_off,x
        inx
        cpx #PROPFONT_COLS
        bne -

        lda #0
-
        sta screen_base + hud_row_off,x
        inx
        cpx #18
        bne -
        rts

; (arr) = 1-based glyph string; Y = start index
PrintSpecFontString
        sty stringstart

        jsr PutFontUDGsOnScreen

        lda #0
        sta stringxdiv
        lda #1                      ; 1 px gap before first glyph
        sta stringxmod

        ldy stringstart
        sty stringindex
---
        ; read a char
        ldy stringindex
        lda (arr),y
        beq ++
        iny
        sty stringindex
        sec
        sbc #1
        sta stringcur

        lda stringcur
        jsr GetCharDefAddr

        ldy #0
        sty stringrow
--
        lda (arr2),y

        sta stringleft
        lda #0
        ldx stringxmod
        beq +
-
        lsr stringleft
        ror
        dex
        bne -
+
        sta stringright

        lda stringxdiv
        clc
        adc stringrow
        tax
        lda propfont_udg,x
        eor stringleft
        sta propfont_udg,x
        lda propfont_udg+8,x
        eor stringright
        sta propfont_udg+8,x

        inc stringrow
        ldy stringrow
        cpy #8
        bne --

        lda stringcur
        jsr GetCharWidth
        clc
        adc stringxmod
        sta stringxmod
        lda stringxmod
        and #8
        clc
        adc stringxdiv
        sta stringxdiv
        lda stringxmod
        and #7
        sta stringxmod

        jmp ---
++
        rts
