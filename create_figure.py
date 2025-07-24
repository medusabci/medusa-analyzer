import os
from PIL import Image
import matplotlib.pyplot as plt

# Ruta base
base_path = r"D:\Proyectos\medusa-analyzer"

# Nombres de archivo en orden
image_files = [
    "psd_comparativo_con_bandas.png",
    "topoplot_relative_alpha.png",
    "topoplot_aec_80.png"
]

# Cargar imágenes
images = [Image.open(os.path.join(base_path, img)) for img in image_files]

# Crear figura con subplots
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 15))

# Quitar todo el espacio entre subplots
plt.subplots_adjust(left=0, right=1, top=1, bottom=0, hspace=0)

# Mostrar imágenes
for ax, img in zip(axes, images):
    ax.imshow(img)
    ax.axis('off')  # Quitar ejes

plt.savefig("figura_final.png", dpi=300);
plt.show()


