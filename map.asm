ResetGame

SHOW_TITLE = 1

!if SHOW_TITLE {

    lda #ROOM_TITLE
    sta map
    jsr LoadRoom
    jsr TitleScreen
}

    lda #ROOM_START
    sta map
    lda #8
    sta men

    ldx #$ff
    stx music_enabled
    inx ; x now 0
    stx music_key_prev
    stx items_collected
    stx willy_hidden
    stx xadd
    stx edge_skip_draw
    stx fall_death_respawn
    stx music_index
    stx music_delay

    txa
    ldy #pickup_got_last - pickup_got
-
    sta pickup_got,y
    dey
    bpl -

    inx ; x now 1
    stx initial_room_load       ; first room load uses @spawn from meta

	rts

DrawMap
    lda #0
    sta dead
    lda initial_room_load
    bne drawmap_first_room
    lda fall_death_respawn
    beq +
    lda safe_px
    sta px
    lda safe_py
    sta py
    lda safe_map
    sta map
    jsr SaveSpawn
    lda #0
    sta fall_death_respawn
    beq ++
+
    lda spawn_px
    sta px
    lda spawn_py
    sta py
++
    lda #0
    sta use_room_spawn
    jmp LoadRoom               ; tail call — LoadRoom draws via DrawPlayerBody
drawmap_first_room
    lda #1
    sta use_room_spawn          ; new game - @spawn from room meta
    jsr LoadRoom
    jsr SaveSpawn
    lda #0
    sta use_room_spawn
    sta initial_room_load
	rts

CheckRoomEdge
    ; prepare new coordinates
    ldx px
    ldy py

    ; check west
    lda meta_content_conn + 3
    cpx #$ff
    bne +
    ldx #91
    bne .do_room_change ; always
+
    ; check east
    lda meta_content_conn + 1
    cpx #92
    bne +
    ldx #0
    beq .do_room_change ; always
+
    ; check north
    lda meta_content_conn
    cpy #128
    bcc +   ; branch if Y < 128
    ldy #104
    bne .do_room_change ; always
+
    ; check south
    lda meta_content_conn + 2
    cpy #111
    bcc +    ; branch if Y < 111
    ldy #0
    beq .do_room_change ; always
+
    clc ; draw player after, since we didn't transition
    rts

.do_room_change
    sta map
    inc safe_transition_count
    stx px
    sty py
    sty last_py  ; if we change from bottom to top of room, this would be huge
    sty newy

    lda #0
    sta use_room_spawn          ; edge transition - px/py already set, not @spawn
    jsr LoadRoom
    jsr SaveSpawn

    jsr do_falling_ramp_check

    sec ; don't draw player after, since we did transition
    rts
