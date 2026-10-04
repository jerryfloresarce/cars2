# -*- coding: utf-8 -*-
"""analisis_mat.py - copia de kn5_writer_opt.analizar_material() (sin importarlo: su modulo ejecuta main())
para los scripts de 03_blender/_rev/color_ac. Devuelve el color que el writer pone en el KN5 (diffuse_color si
el Base Color esta enlazado), alpha, imagen de color (nombre), factor de la mezcla y medias de la imagen."""
import numpy as np


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4)).astype(np.float32)


def _socket(node, identifier):
    for s in node.inputs:
        if s.identifier == identifier:
            return s
    return None


def analizar(m, medias=True):
    info = {'name': m.name, 'color': [float(c) for c in m.diffuse_color[:3]], 'alpha': 1.0,
            'img': None, 'factor': 1.0, 'proj': 'FLAT', 'img_media_lin': None, 'img_std_lin': None}
    nt = m.node_tree
    if not nt:
        return info
    pr = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if pr:
        a = pr.inputs['Alpha']
        if not a.is_linked:
            info['alpha'] = float(a.default_value)
        bc = pr.inputs['Base Color']
        if not bc.is_linked:
            info['color'] = [float(c) for c in bc.default_value[:3]]
        for k in ('Roughness', 'Metallic', 'Specular IOR Level', 'Emission Strength', 'Transmission Weight'):
            s = pr.inputs.get(k)
            if s is not None and not s.is_linked:
                info[k.lower().replace(' ', '_')] = float(s.default_value)
    tex = None
    for n in nt.nodes:
        if (n.bl_idname == 'ShaderNodeTexImage' and n.image
                and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked):
            tex = n
            break
    if tex is None:
        return info
    info['img'] = tex.image.name
    info['proj'] = tex.projection
    mul = nt.nodes.get('TEX_multiplicar')
    if mul and mul.bl_idname == 'ShaderNodeMix':
        sf = _socket(mul, 'Factor_Float')
        info['factor'] = float(sf.default_value) if (sf is not None and not sf.is_linked) else 0.6
    if not medias:
        return info
    try:
        img = tex.image
        n = len(img.pixels)
        w, h = img.size
        if n and w and h:
            buf = np.empty(n, np.float32)
            img.pixels.foreach_get(buf)
            lin = srgb_to_lin(buf.reshape(h, w, -1)[:, :, :3])
            info['img_media_lin'] = [float(v) for v in lin.mean(axis=(0, 1))]
            lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            info['img_std_lin'] = float(lum.std() / max(lum.mean(), 1e-4))
    except Exception as e:  # noqa
        print('AVISO imagen', tex.image.name, e)
    return info
