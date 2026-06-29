;
; Catalogue record lookup — stream_ptr from RoomRecordPtrs (bake/catalogue_rooms.asm).
; Pool, sets, and room records are read in place — no copy at boot.
;

!zone catalogue

FindRoomRecord
    lda map
    asl
    tay
    lda RoomRecordPtrs,y
    sta stream_ptr
    lda RoomRecordPtrs+1,y
    sta stream_ptr_hi
    sec
    rts
