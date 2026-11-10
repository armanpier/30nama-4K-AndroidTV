import hermes_dec
print(dir(hermes_dec))
import inspect
import pkgutil

print([mod.name for mod in pkgutil.iter_modules(hermes_dec.__path__)])
