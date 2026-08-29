def do_stuff(n):
    if n == 0:
        return
    print ("foo", n)
    do_stuff(n - 1)
    print("bar", n)
    return
do_stuff(3)