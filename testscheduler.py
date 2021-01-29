# from apscheduler.schedulers.blocking import BlockingScheduler
#
# import random
# def tick():
#     try:
#         var = random.sample(range(1, 100), 3) #random.sample(population, k) will return a k length list of unique elements chosen from population
#         # done for random sampling without replacement)
#         print(type(var))
#         print(var)
#     except ValueError:
#         print('Sample size exceeded population size.')
#
#
# if __name__ == '__main__':
#     scheduler = BlockingScheduler()
#     scheduler.add_executor('processpool')
#     scheduler.add_job(tick, 'interval', seconds=5)
#
#     try:
#         scheduler.start()
#     except (KeyboardInterrupt, SystemExit):
#         pass


from apscheduler.schedulers.background import BackgroundScheduler

import time


import random
def tick():
    try:
        var = random.sample(range(1, 100), 3) #random.sample(population, k) will return a k length list of unique elements chosen from population
        # done for random sampling without replacement)
        print(type(var))
        print(var)
    except ValueError:
        print('Sample size exceeded population size.')


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=5)
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
