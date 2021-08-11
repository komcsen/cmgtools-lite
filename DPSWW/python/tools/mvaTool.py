import os, ROOT
from array import array
ROOT.TMVA.PyMethodBase.PyInitialize()
class MVAVar:
    def __init__(self,name,type='f',func=None):
        self.name = name
        if func != None:
            self.func = func
        else:
            if ":=" in self.name:
                self.expr = self.name.split(":=")[1]
                self.func = lambda ev : ev.eval(self.expr)
            else:
                self.func = lambda ev : ev[self.name]
        self.type = type
        self.var  = array('f',[0.]) #TMVA wants ints as floats! #array(type,[0 if type == 'i' else 0.])
    def set(self,ev): 
        self.var[0] = self.func(ev)

class MVATool:
    def __init__(self,name,xml,vars,specs=[],nClasses=1,rarity=False):
        self.name = name
        #        TMVA.PyMethodBase.PyInitialize()
        self.reader = ROOT.TMVA.Reader("Silent")
        self.vars  = vars
        self.specs = specs
        self.nClasses = nClasses

        for v in vars:  self.reader.AddVariable(v.name,v.var)
        for s in specs: self.reader.AddSpectator(s.name,s.var)
        #print "Would like to load %s from %s! " % (name,xml)
        self.reader.BookMVA(name,xml)
        self.rarity = rarity
        if self.rarity and self.nClasses!=1: raise RuntimeError, 'not implemented'
    def __call__(self,ev): 
        for s in self.vars:  s.set(ev)
        for s in self.specs: s.set(ev)
        return (self.reader.EvaluateMVA(self.name) if self.nClasses==1 else self.reader.EvaluateMulticlass(self.name)[self.nClasses-2]) if not self.rarity else self.reader.GetRarity(self.name)  
        #return (self.reader.EvaluateMVA(self.name))

class CategorizedMVA:
    def __init__(self,catMvaPairs):
        self.catMvaPairs = catMvaPairs
    def __call__(self,lep):
        for c,m in self.catMvaPairs:
            if c(lep): return m(lep)
        return -99.



