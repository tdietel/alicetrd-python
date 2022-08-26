import oscilloscopeRead.dso1kb as dso1kb
interface = dso1kb.getInterfaceName()
dso = dso1kb.Dso(f'/dev/{interface}')
dso.getRawData(True, 1)
dso.getRawData(True, 2)
dso.getRawData(True, 4)
print(dso.getByteData([1, 2, 4]))