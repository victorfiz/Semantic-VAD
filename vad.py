import time
import random


def random_gen(socketio):
    while True:
        rand_num = random.randint(1, 100)
        socketio.emit('new_number', {'number': rand_num})
        time.sleep(1)




