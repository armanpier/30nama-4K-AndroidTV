import hermes_dec, os
path = hermes_dec.__path__[0]
for root, dirs, files in os.walk(path):
    print(root, files)
