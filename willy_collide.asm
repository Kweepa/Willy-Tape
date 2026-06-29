!zone willy_implementation

try_touch
    jsr GetCollision
    cmp #TILE_SOLID
    beq do_block
    clc
    rts
do_block
    sec
    rts

try_touch_below
    jsr GetCollision
    cmp #TILE_EMPTY
    beq no_hit
    cmp #TILE_ITEM
    beq no_hit
    cmp #TILE_CONVEYOR
    bne check_floor
    jmp DoBelt                 ; tail call — must exit with C=1
check_floor
    cmp #TILE_PLATFORM
    beq hit
    cmp #TILE_SOLID
    beq hit
no_hit
    clc
    rts
hit
    sec
    rts

CollideLeftRight
    lda left_right_ctr
    bne lr_out

    ; x=0 moving left, x=1 moving right (from sign of xadd: $FF / $01)
    ldx xadd
    beq lr_out
    inx
    txa
    lsr
    tax

    ; Side probes: lr_touch is 2 cols (move left / move right) x 3 rows
    ; (a/b/c).  x picks the col; rows are map offsets at $E2-$E7.
    ; Left: probe only at px&3==0 (char boundary).  Right: only at
    ; px&3==3 (last px before next boundary) — right col uses far offsets
    ; 26/50/74 so we look past the sprite, not inside it.  px&3==1,2: no
    ; probe either direction (sub-pixel steps between check points).
    ; Gate: (left & px&3==0) or (right & px&3==3); cmp #1 / rol maps dir 0->0, 1->3.
    cmp #1
    rol
    sta tmp
    lda px
    and #$03
    cmp tmp
    bne lr_move

    ; lr_touch at px=0 wraps to col 23 — never probe at left screen edge
    cpx #0
    bne +
    lda px
    beq lr_move
+
    ; same at px=91 before east transition at px=92
    cpx #1
    bne lr_do_touch
    lda px
    cmp #91
    beq lr_move
lr_do_touch
    ldy lr_touch_a,x
    jsr try_touch
    bcs lr_out
    ldy lr_touch_b,x
    jsr try_touch
    bcs lr_out
    ldy lr_touch_c,x
    ; lower side probe when py&7!=0 (misaligned feet).  On ramps feet are
    ; always misaligned; UP_LEFT baked ry+2 lowers py so c hits W under \
    ; tiles and blocks climbing — skip c while already on the ramp.
    lda is_on_ramp
    bne lr_move
    lda py
    and #$07
    beq lr_move
    jsr try_touch
    bcs lr_out
lr_move
    ; px += xadd (xadd is +1 / -1 as $01 / $FF)
    lda px
    clc
    adc xadd
    sta px
    tax
    ldy py
    jsr ConvertXYToScreenAddr
    jsr calculate_ramp_y
    ; xadd is guaranteed nonzero here (early return above), so just gate the
    ; walking-ramp snap on was_on_ground OR is_on_ramp.
    lda was_on_ground
    ora is_on_ramp
    beq +
    jsr do_walking_ramp_check
+
    lda is_on_ramp
    beq +
    ldx px
    ldy py
    jsr ConvertXYToScreenAddr
    lda #1
    sta on_ground
    lda #27
    sta inairtime
+
lr_out
    rts

Collide
    lda willy_hidden
    beq collide_active
    rts
collide_active
    lda meta_content_room_has_rope ; skip if !(rope && holding)
    and rope_willy_is_holding
    beq collide_body
    jsr RopePlayerInput          ; climb / descend / jump / fall-off
    lda rope_willy_is_holding
    beq collide_body             ; released this frame -> normal physics applies jump/fall
    jsr rope_draw_maybe          ; gated draw; snaps willy to the held segment
    jmp DrawPlayerEntry          ; skip gravity while carried
collide_body
    lda py
    sta last_py
    lda on_ground
    bne +
    sta belt_active
+
    lda on_ground
    sta was_on_ground
    lda inairtime
    cmp #70
    bcs +
    inc inairtime
+
    lda inairtime
    cmp #27
    bcs +
    ldx #0
    stx was_on_ground
+
    cmp #52 ; comparing inairtime
    bne +
    lda #0
    sta xadd
+
    lda #0
    sta on_ground
    sta mov
    ldx px
    ldy py
    jsr ConvertXYToScreenAddr
    jsr CollideLeftRight
    jsr calculate_ramp_y
    lda py
    and #$f8
    sta align_tmp
	lda inairtime
	cmp #51
	bcc +
	lda #51
+
    tax
    lda jumptab,x
    clc
    adc py
    sta newy

    ; play jump sound
    ldy was_on_ground
    bne +
    txa ; clamped inairtime in X
    lsr
    tax
    ldy jumpnotes,x
    sty $900c
    lda #2
    sta $900e
    ; end play jump sound
+

    lda inairtime
    cmp #27
    bcs collide_down
    lda newy
    and #$f8
    cmp align_tmp
    bne +
    jmp collide_jmp_move_up_down
+
    lda py
    cmp #8
    bcs jump_above_check
    ldy meta_content_conn   ; north @conn; allow exit without tile probe
    bpl collide_jmp_move_up_down
    lda #27
    sta inairtime
    lda #0
    sta newy
    beq collide_jmp_move_up_down
jump_above_check
    ldy #0
    jsr try_touch
    bcc +
    jmp hit_above
+
    ldy #1
    jsr try_touch
    bcc +
    jmp hit_above
+
    bcc collide_jmp_move_up_down
+
collide_down
    lda on_ground
    ora is_on_ramp
    ora xadd
    bne +
    jsr do_falling_ramp_check
+
    lda is_on_ramp
    beq +
    jmp check_jump
+
    lda py
    and #$07
    beq look_below_2
    lda newy
    and #$f8
    cmp align_tmp
    beq collide_jmp_move_up_down
+
    ldy #96
    jsr try_touch_below
    bcs hit_below
    iny
    jsr try_touch_below
    bcs hit_below
    bcc collide_jmp_move_up_down
hit_below
    jsr try_fall_death

    lda #1
    sta on_ground
    lda #27
    sta inairtime

    lda newy
    and #$f8
    sta newy
    jmp collide_jmp_move_up_down
collide_jmp_move_up_down
    jmp move_up_down
look_below_2
    lda was_on_ground
    beq +
    lda #0
    sta xadd
+
    ldy #72
    jsr try_touch_below
    bcs +                    ; leading foot grounded -> still probe trailing foot
    iny
    jsr try_touch_below
    bcc collide_jmp_move_up_down
    bcs check_jump
+
    ldy #73
    jsr try_touch_below      ; a belt here overrides the platform touch (carries Willy on)
check_jump
    lda xadd
    bne +
    sta belt_active          ; fully off the belt -> release lock
+
    lda #1
    sta on_ground
    lda #27
    sta inairtime
    lda jumpIsPressed
    beq collide_end
    lda #0
    sta inairtime
    sta is_on_ramp
    beq collide_end
move_up_down
    lda #1
    sta mov
collide_done
collide_end
    lda mov
    beq collide_dont_move_y
    lda newy
    sta py
collide_dont_move_y
    lda on_ground
    beq +
    lda belt_active
    bne +                       ; If conveyor is actively pushing us, do NOT clear xadd!
    ; lda #0 ; see test result above
    sta xadd
+
    lda on_ground
    beq +
    lda dead
    bne +
    lda map
    sta safe_map
    lda px
    sta safe_px
    lda py
    sta safe_py
    lda #0
    sta safe_transition_count
+
    lda meta_content_room_has_rope
    beq collide_draw_player
    jsr rope_draw_maybe          ; animate rope + attach detection via DrawPlayer/coll_check
collide_draw_player
    jmp DrawPlayerEntry        ; tail call — was jsr/rts
hit_above
    lda #27
    sta inairtime
    lda py
    and #$f8
    sta newy
    jmp collide_jmp_move_up_down

lr_touch_a
    !byte 23, 26                                    ; CollideLeftRight
lr_touch_b
    !byte 47, 50
lr_touch_c
    !byte 71, 74

jumptab
    ; Collide jump arc
    !byte -2, -1, -2, -1, -2, -1, -1, -1, -2, -1, -1, 0, -1, -1, -1, 0, -1, 0, -1, 0, 0, -1, 0, 0, 0, 0, 0
    !byte 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 2, 1, 1, 1, 2, 1, 2, 1, 2

jumpnotes
    !byte 150,155,160,165,170,175,180,185,190
    !byte 195,200,205,210,215,210,205,200,195
    !byte 190,185,180,175,170,165,160,155,150
