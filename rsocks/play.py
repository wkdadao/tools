class Rain(object):
    pass

def parse(rain):
    print('parse')

    ver = None
    cmd = None
    addr = None

    # ver
    while len(rain.buf) < 1:
        yield 'wait for ver'

    ver = rain.buf[0]
    rain.buf = rain.buf[1:]
    print('ver:' + ver)

    # cmd
    while len(rain.buf) < 2:
        yield 'wait for cmd'

    cmd = rain.buf[0:2]
    rain.buf = rain.buf[2:]
    print('cmd:' + cmd)

    # addr
    while len(rain.buf) < 4:
        yield 'wait for addr'

    addr = rain.buf[0:4]
    rain.buf = rain.buf[4:]
    print('addr:' + addr)
    return 'done'

rain = Rain()
rain.buf = "0C"
it = parse(rain)
print(next(it))
rain.buf = rain.buf + 'M'
print(next(it))
print(next(it))
rain.buf = rain.buf + 'HOST'
print(next(it))