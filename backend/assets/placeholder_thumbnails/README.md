# Placeholder song thumbnails

Images that metadata APIs send in place of a song's cover: a station or site
logo, or a generic placeholder. A song thumbnail whose file is byte-identical
to one of these is not shown (`radio_crestin/tasks/check_song_thumbnail.py`).

To add one, save the file exactly as its source serves it (`curl -o`), not a
re-saved or resized copy: only identical bytes match.

| File | Source |
|---|---|
| `aripisprecer_na.png` | Aripi Spre Cer, `*/na.png` |
| `aripisprecer_instrumental.jpg` | Aripi Spre Cer Instrumental, under a URL per song ("VA INST") |
| `aripisprecer_colinde.jpg` | Aripi Spre Cer, colinde |
| `aripisprecer_framed.png` | Aripi Spre Cer, framed logo under a URL per song |
| `aripisprecer_music_note.jpg` | Aripi Spre Cer, generic music note |
| `crestinaudio.png` | CrestinAudio.ro logo, via Aripi Spre Cer |
| `radio_de_cuvant_radio_co.png` | radio.co station logo of Radio de Cuvânt |
| `radio_de_cuvant_cuvantul.png` | Radio de Cuvânt "Cuvântul" image, under a radio.co URL per sermon |
| `radiofiladelfia_no_cover.jpg` | Radio Filadelfia, `no_cover_image.jpg` |
