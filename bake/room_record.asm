; Room catalogue record — meta8 byte 6 feature flags.
; Each set bit implies optional data blocks follow in the record (see mkcatalogue.py).

FLAG_NASTY    = %00000001  ; hazard tiles in tilemap
FLAG_RAMP     = %00000010  ; ramp overlay (2 B) follows pickup
FLAG_CONVEYOR = %00000100  ; conveyor overlay (2 B) follows pickup
FLAG_ROPE     = %00001000  ; room has rope
FLAG_ARROW    = %00010000  ; arrow block (5 B) before guardians

; tile_udg block: floor + wall + item (24 B); nasty/ramp/belt +8 B each when flagged.
; Type 0 empty UDG is always zero — not stored.
