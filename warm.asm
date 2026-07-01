; One-shot boot @ $1800 (udg_base); VIC setup then straight into the game.
; Overwritten by room UDG load — only needed before first LoadRoom.
; Must not RTS here: txs clears the SYS return address on the stack.

WarmStart
 
    lda #$7f
    sta $911d                   ; VIA #2 IER - disable all enables
    sta $911e                   ; T2CL - preset timer 2 low

    cld                         ; clear bcd mode
    ldx #$ff                    ; reset stack
    txs

    jsr $fdf9                   ; IOINIT — keyboard matrix / VIA defaults
    sei

    ; $eb15 is minimal no-op interrupt handler
    lda #$15
    sta $0314
    lda #$eb
    sta $0315

    ldy #9
-
    ldx .vic_offset,y
    lda .vic_val,y
    sta $9000,x
    dey
    bpl -

    jmp start_game

    ; horizontal centering, vertical centering,
    ; num columns (plus high bit for screen), num rows,
    ; screen and udg loc, voices, volume
    ; $9002 bit7=0 -> screen $1000 + color $9400 (16K tape layout)
    ; $9002 bit7=1 -> screen $1E00 + color $9600 (disk / unexpanded layout)
    ; $9005 $CE -> video block 12 ($1000) + charset block 14 ($1800)
.vic_offset
    !byte 0, 1, 2, 3, 5, $a, $b, $c, $d, $e
.vic_val
    !byte 10, 50, 24, 17<<1, $ce, 0, 0, 0, 0, 10
