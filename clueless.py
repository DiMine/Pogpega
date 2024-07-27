# Various functions from Clueless that are extremely helpful, with some slight modifications
# https://github.com/pxlsspace/Clueless

import numpy as np
from PIL import ImageColor


# https://github.com/pxlsspace/Clueless/blob/ddf69363ba786104ac36014740876b2930dbc471/src/utils/pxls/pxls_stats_manager.py#L183
def palettize_array(array, palette):
    """Convert a numpy array of palette indexes to a color numpy array
    (RGBA). If a palette is given, it will be used to map the array, if not
    the current pxls palette will be used"""
    colors_list = []
    for color in palette:
        rgb = ImageColor.getcolor(color, "RGBA")
        colors_list.append(rgb)
    colors_dict = dict(enumerate(colors_list))
    colors_dict[255] = (0, 0, 0, 0)

    img = np.stack(np.vectorize(colors_dict.get)(array), axis=-1)
    return img.astype(np.uint8)

# https://github.com/pxlsspace/Clueless/blob/ddf69363ba786104ac36014740876b2930dbc471/src/utils/image/image_utils.py#L249
def hex_to_rgb(hex: str, mode="RGB"):
    """convert a hex color string to a RGB tuple
    ('#ffffff' -> (255,255,255) or 'ffffff' -> (255,255,255)"""
    if "#" in hex:
        return ImageColor.getcolor(hex, mode)
    else:
        return ImageColor.getcolor("#" + hex, mode)