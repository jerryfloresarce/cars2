# -*- coding: utf-8 -*-
"""comprobar_rutas_blend.py - Comprueba SIN abrir Blender que un .blend no lleva rutas de imagen RELATIVAS ('//...').
Fase visual F1 r2 (director_f1_r1.md 1): escena_candidata.blend salia MAGENTA fuera de 03_blender/ porque construir_pista.py
guardaba desde --factory-startup con relative_remap=True. Red de seguridad para _rev/pipeline_escena.sh (integrador).

  "C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe" comprobar_rutas_blend.py <fichero.blend> [...]
  (necesita zstandard: el python de Blender lo trae; el del sistema no. Los .blend de 5.1 van comprimidos con zstd.)

Sale 0 si ninguna cadena '//<ruta>.png|.jpg|.exr|.hdr|.tga|.tif' aparece en los bloques de datos; 1 si hay alguna; 2 si no se
puede leer. Imprime las rutas encontradas (unicas) y cuantas absolutas de texturas/ hay, para el log.
"""
import os
import re
import sys

ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'
EXT = rb'(?:png|jpg|jpeg|exr|hdr|tga|tif|tiff|bmp|dds)'
REL = re.compile(rb'//[^\x00]{1,200}?\.' + EXT, re.IGNORECASE)
ABS = re.compile(rb'[A-Za-z]:\\[^\x00]{1,240}?\.' + EXT, re.IGNORECASE)


def leer(ruta):
    with open(ruta, 'rb') as fh:
        datos = fh.read()
    if datos[:4] == ZSTD_MAGIC:
        import io
        import zstandard
        # los .blend zstd de Blender son varios frames concatenados + un frame 'skippable' con la tabla de seek:
        # read_across_frames los encadena y salta el skippable
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(datos), read_across_frames=True) as rd:
            return rd.read()
    return datos


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    rc = 0
    for ruta in argv:
        try:
            datos = leer(ruta)
        except Exception as e:
            print('%s: NO LEIDO (%s)' % (ruta, e))
            rc = max(rc, 2)
            continue
        if not datos.startswith(b'BLENDER'):
            print('%s: no parece un .blend descomprimido (cabecera %r)' % (ruta, datos[:8]))
            rc = max(rc, 2)
            continue
        rel = sorted(set(m.group(0).decode('utf-8', 'replace') for m in REL.finditer(datos)))
        abs_ = sorted(set(m.group(0).decode('utf-8', 'replace') for m in ABS.finditer(datos)))
        abs_tex = [a for a in abs_ if 'texturas' in a.lower()]
        print('%s: %.1f MB descomprimido | rutas de imagen relativas: %d | absolutas: %d (de texturas/: %d)'
              % (ruta, len(datos) / 1e6, len(rel), len(abs_), len(abs_tex)))
        for r in rel[:40]:
            print('   RELATIVA  ', r)
        if rel:
            print('   -> FALLO: esas imagenes saldran MAGENTA si el .blend se copia a otra carpeta (director_f1_r1.md 1)')
            rc = max(rc, 1)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
