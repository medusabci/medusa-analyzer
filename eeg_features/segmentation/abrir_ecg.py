import medusa.components
from medusa import components
from medusa import ecg

path = r'D:\Proyectos\Videojuego\data\S2\R3.rec.bson'


registro = medusa.components.Recording.load(path)

ecg = registro.eeg.signal

print('hola')
