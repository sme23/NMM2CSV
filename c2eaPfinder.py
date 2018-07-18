caches = {}

def getOrSetNew(dicToCheck, key, newFunc):
    if key not in dicToCheck:
        dicToCheck[key] = newFunc()
    return dicToCheck[key]

def memoize(name = None):
    def decorator(f):
        global caches
        # If we are given a valid name for the function, associate it with that entry in the cache.
        if name is not None:
            cache = getOrSetNew(caches, name, lambda: {})
        else:
            cache = {}
        def g(*args):
            return getOrSetNew(cache, args, lambda: f(*args))
        # Set the cache as a function attribute so we can access it later (say for serialization)
        g.cache = cache
        return g
    return decorator

@memoize()
def readRom(romFileName):
    words = []
    with open(romFileName, 'rb') as rom:
        while True:
            word = rom.read(4)
            if word == b'':
                break
            words.append(word)
    return words

@memoize(name = 'pointerOffsets')
def pointerOffsets(romFileName, value):
    return tuple(pointerIter(romFileName, value))

def pointerIter(romFileName, value):
    target = value.to_bytes(4, 'little')
    words = readRom(romFileName)
    return (i<<2 for i,x in enumerate(words) if x==target)
