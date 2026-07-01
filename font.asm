;
; Proportional font — ported from Miner-main/font.asm.
; Title strings in catalogue use 1-based compact glyph bytes (0 = end; N = glyph N-1).
; Glyph patterns: font_glyphs @ $1A20 (arrow_udgs.asm). Composite canvas: chr 7–21.
;

!zone font

; A = compact glyph index -> arr2 = font_glyphs + index*8
GetCharDefAddr
        ldx #0
        stx arr2+1
        asl
        rol arr2+1
        asl
        rol arr2+1
        asl
        rol arr2+1
        adc #<font_glyphs
        sta arr2
        lda arr2+1
        adc #>font_glyphs
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
        ; fill the characters with 0; 0 = normal video (eor below)
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
        cpx #19
        bne -
        rts

; (arr) = 1-based glyph string; Y = start index
; propfont_first = first composite UDG chr (PROPFONT_CHR for HUD titles).
PrintSpecFontString
        sty stringstart
        lda #PROPFONT_CHR
        sta propfont_first
        jsr PutFontUDGsOnScreen
        ldy stringstart
        ; fall through

; Same render path; caller sets propfont_first and arr.
PrintSpecFontStringBody
        sty stringindex
        lda #0
        sta stringxdiv
        lda #1                      ; 1 px gap before first glyph
        sta stringxmod
        lda propfont_first
        asl
        asl
        asl
        sta udg_ptr
        lda #>udg_base
        adc #0
        sta udg_ptr+1
---
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
        tay
        lda (udg_ptr),y
        eor stringleft
        sta (udg_ptr),y
        tya
        clc
        adc #8
        tay
        lda (udg_ptr),y
        eor stringright
        sta (udg_ptr),y

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
