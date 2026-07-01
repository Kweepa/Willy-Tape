; Room catalogue record — meta8 byte 6 feature flags.
; Bits 0-5 align with UDG chr 1-6; bits 6-7 are rope / arrow (see mkcatalogue.py).

FLAG_FLOOR    = %00000001  ; chr 1 floor UDG (always set)
FLAG_WALL     = %00000010  ; chr 2 wall UDG (always set)
FLAG_NASTY    = %00000100  ; chr 3 hazard UDG when tilemap has nasty
FLAG_RAMP     = %00001000  ; chr 4 ramp UDG + 2 B ramp overlay after pickup
FLAG_CONVEYOR = %00010000  ; chr 5 belt UDG + 2 B conveyor overlay after pickup
FLAG_ITEM     = %00100000  ; chr 6 pickup UDG (always set)
FLAG_ROPE     = %01000000  ; room has rope
FLAG_ARROW    = %10000000  ; arrow block (1 B) before guardians

; tile_udg block: 8 B per set flag in chr order 1-6; type 0 empty is always zero — not stored.
