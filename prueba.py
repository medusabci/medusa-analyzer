
import medusa
from medusa import components

path = r'C:\Users\beapa\PycharmProjects\medusa-analyzer\Example signals\R3.rec.bson'

eeg = components.Recording.load(path)
print(eeg)