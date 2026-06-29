; Room catalogue record — meta8 byte 6 feature flags.
; Each set bit implies optional data blocks follow in the record (see mkcatalogue.py).

FLAG_NASTY    = %00000001  ; hazard tiles; nasty UDG (8 B) in tile_udg block
FLAG_RAMP     = %00000010  ; ramp overlay (3 B) + ramp UDG (8 B)
FLAG_CONVEYOR = %00000100  ; conveyor overlay (3 B, incl. belt dir) + belt UDG (8 B)
FLAG_ROPE     = %00001000  ; room has rope
FLAG_ARROW    = %00010000  ; arrow block (5 B) follows tile_udg

; Always in tile_udg block (no flag): floor (1), wall (2), pickup (6) — 24 B.
; Type 0 empty UDG is always zero — not stored.
