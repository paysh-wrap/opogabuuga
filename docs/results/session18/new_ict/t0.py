import time, lib, sys
t=time.time(); lib.load(); print("load",time.time()-t)
t=time.time(); c=lib.gen("AM",1,"all",start="2024-01-02",end="2024-06-30"); print("gen",len(c),time.time()-t)
t=time.time(); df=lib.simulate(c,"mid",2.0); print("sim",len(df),time.time()-t)
print(lib.stats(lib.select(df)))
print(df.head())
