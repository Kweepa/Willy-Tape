; Unified per-room hooks (disk build baked these into each room PRG).

!zone tape_runtime

FlickerItem
    rts
    !fill item_flicker_prefix_bytes - 1, 0

AnimateConveyors
    rts
    !fill conveyor_prefix_bytes - 1, 0

DoBelt
    sec                         ; willy.asm tail call expects C=1
    rts
    !fill do_belt_prefix_bytes - 2, 0

tile_color_src
    !byte 1, 5, 7, 3, 2, 6       ; WHT GRN YEL CYN RED BLU — types 0-5

item_draw
    rts
    !fill meta_content_item_draw_size - 1, 0

item_erase
    rts
    !fill meta_content_item_erase_size - 1, 0
