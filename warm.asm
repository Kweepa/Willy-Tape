; One-shot boot; VIC setup then straight into the game.
; Must not RTS here: txs clears the SYS return address on the stack.

WarmStart
 
    lda #$7f
    sta $911d                   ; VIA #2 IER - disable all enables
    sta $911e                   ; T2CL - preset timer 2 low

    cld                         ; clear bcd mode
    ldx #$ff                    ; reset stack
    txs

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

    // CONTINUE HERE

    jmp start_game

    ; horizontal centering, vertical centering,
    ; num columns (plus high bit for screen), num rows,
    ; screen and udg loc, voices, volume
.vic_offset
    !byte 0, 1, 2, 3, 5, $a, $b, $c, $d, $e
.vic_val
    !byte 10,50,$98,17<<1,$ce,0,0,0,0,10
