; Unified per-room hooks (disk build baked these into each room PRG).

!zone tape_runtime

; Draw pickup chr and cycle cell colour while pickup_got for this room is clear.
; pickup_scr / pickup_col set at load (absolute screen + colour pointers in ZP).

FlickerItem
    ldx map
    lda pickup_got,x
    bne fi_done
    lda pickup_scr+1
    bmi fi_done
    ldy #0
    lda #ITEM_CHR
    sta (pickup_scr),y
    lda (pickup_col),y
    clc
    adc #1
    and #7
    sta (pickup_col),y
fi_done
    rts

conveyor_udg = $1800 + 8 * TILE_CONVEYOR

AnimateConveyors
    lda left_right_ctr
    bne ++
    lda meta_content_belt
    beq ++
    bpl +

    lda conveyor_udg
    asl
    rol conveyor_udg
    lda conveyor_udg + 2
    lsr
    ror conveyor_udg + 2
    rts
+
    lda conveyor_udg
    lsr
    ror conveyor_udg
    lda conveyor_udg + 2
    asl
    rol conveyor_udg + 2
++
    rts

DoBelt
    ; @belt -1 pushes left: oppose key is right
    ; @belt 1 pushes right: oppose key is Left
    ; belt_active starts 0, becomes 1 when you stop opposing it

    ldx #0
    lda meta_content_belt
    beq .belt_end

    bpl .belt_right
    ldx #1
.belt_right

    lda belt_active
    bne ++
    lda leftIsPressed,x ; left or right
    beq +

    ; still opposing so go opposite direction to belt
    lda meta_content_belt
    eor #$fe ; flip -1 <-> 1
    bne .belt_tail
+
    ; belt starts inactive, but when you release the
    ; opposing key, it goes active
    lda #1
    sta belt_active
++
    lda meta_content_belt
    sta lastxmove

.belt_tail
    sta xadd
.belt_end
    sec
    rts

tile_color_src
    !byte 1, 5, 7, 3, 2, 6       ; WHT GRN YEL CYN RED BLU — types 0-5

item_draw
    rts

item_erase
    rts

