import time
with open("test_launch.txt", "w") as f:
    f.write(f"Started at {time.ctime()}\n")
time.sleep(10)
with open("test_launch.txt", "a") as f:
    f.write(f"Finished at {time.ctime()}\n")
