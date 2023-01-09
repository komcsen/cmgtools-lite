import ROOT
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
import inspect

class CombinedObjectTaggerForCleaning(Module):

    def __init__(self,label,
                 looseLeptonSel = lambda l : True,
                 cleaningLeptonSel = lambda l : True,
                 FOLeptonSel = lambda l : True,
                 tightLeptonSel = lambda l : True,
                 FOTauSel = lambda t : True,
                 tightTauSel = lambda t : True,
                 selectJet = lambda j : True,
                 selectFatJet = lambda f : True,
                 coneptdef = lambda l : l.pt,
                 debug=False):
        self.label = "" if (label in ["",None]) else ("_"+label)

        self.lepSelYearDependent = False
        for func in [looseLeptonSel,cleaningLeptonSel,FOLeptonSel,tightLeptonSel]:
            if len(inspect.getargspec(func)[0])>1: self.lepSelYearDependent=True
        self.looseLeptonSel = (lambda lep,year,subera: looseLeptonSel(lep)) if len(inspect.getargspec(looseLeptonSel)[0])==1 else looseLeptonSel
        self.cleanLeptonSel = (lambda lep,year,subera: cleaningLeptonSel(lep)) if len(inspect.getargspec(cleaningLeptonSel)[0])==1 else cleaningLeptonSel # applied on top of looseLeptonSel
        self.fkbleLeptonSel = (lambda lep,year,subera: FOLeptonSel(lep)) if len(inspect.getargspec(FOLeptonSel)[0])==1 else FOLeptonSel # applied on top of looseLeptonSel
        self.tightLeptonSel = (lambda lep,year,subera: tightLeptonSel(lep)) if len(inspect.getargspec(tightLeptonSel)[0])==1 else tightLeptonSel # applied on top of looseLeptonSel

        self.fkbleTauSel = FOTauSel
        self.tightTauSel = tightTauSel # applied on top of FOTauSel
        self.selectJet = selectJet
        self.selectFatJet = selectFatJet
        self.coneptdef = coneptdef
        self.debug = debug

    # interface for old code
    def listBranches(self):
        return []

    def __call__(self,event):
        from CMGTools.TTHAnalysis.treeReAnalyzer import Collection
        leps = [l for l in Collection(event,"LepGood","nLepGood")]
        taus = [t for t in Collection(event,"TauGood","nTauGood")]
        jets = [j for j in Collection(event,"Jet","nJet")]
        fatjets = [f for f in Collection(event,"FatJet","nFatJet")]
        self.run(event, leps,taus,jets,fatjets)
        return {}

    # interface for new code
    def analyze(self, event):
        from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection 
        leps = [l for l in Collection(event,"LepGood")]
        taus = [t for t in Collection(event,"Tau")]
        jets = [j for j in Collection(event,"Jet")]
        fatjets = [f for f in Collection(event,"FatJet")]
        self.run(event, leps,taus,jets,fatjets)
        return True

    def run(self, event, leps,taus,jets,fatjets):

        tags = ROOT.CombinedObjectTags(len(leps),len(taus),len(jets),len(fatjets))

        if not self.coneptdef: raise RuntimeError, 'Choose the definition to be used for cone pt'
        for lep in leps: lep.conept = self.coneptdef(lep)

        year = event.year if self.lepSelYearDependent else -1 # to avoid trying to read event.year if not needed (old trees)
        subera = event.subera if hasattr(event, 'subera') else 0

        for i,lep in enumerate(leps):
            if self.looseLeptonSel(lep,year,subera): tags.setLepFlags(i,True,self.cleanLeptonSel(lep,year, subera),self.fkbleLeptonSel(lep,year, subera),self.tightLeptonSel(lep,year, subera),lep.conept)
        for i,tau in enumerate(taus):
            if self.fkbleTauSel(tau): tags.setTauFlags(i,True,self.tightTauSel(tau))
        for i,jet in enumerate(jets):
            if self.selectJet(jet): tags.setJetFlags(i,True)
        for i,fjet in enumerate(fatjets):
            if self.selectFatJet(fjet): tags.setFatJetFlags(i,True)

        setattr(event,'_CombinedTagsForCleaning%s'%self.label,tags)
        return {}

MODULES=[]

if __name__ == '__main__':
    from CMGTools.TTHAnalysis.treeReAnalyzer import EventLoop
    from CMGTools.TTHAnalysis.treeReAnalyzer import Module as CMGModule
    from sys import argv
    file = ROOT.TFile(argv[1])
    tree = file.Get("tree")
    tree.vectorTree = True
    class Tester(CMGModule):
        def __init__(self, name):
            CMGModule.__init__(self,name,None)
            self.sf1 = CombinedObjectTaggerForCleaning("Test",
                                                       looseLeptonSel = lambda lep : lep.sip3d < 8,
                                                       cleaningLeptonSel = lambda lep : True, # cuts applied on top of loose
                                                       FOLeptonSel = lambda lep : lep.pt>30, # cuts applied on top of loose
                                                       tightLeptonSel = lambda lep : lep.conept>10 and lep.jetBTagCSV<0.80 and lep.mvaTTH > 0.75, # cuts applied on top of loose
                                                       FOTauSel = lambda tau: tau.pt > 20 and abs(tau.eta)<2.3 and tau.idMVAOldDMRun2dR03 >= 1,
                                                       tightTauSel = lambda tau: tau.idMVAOldDMRun2dR03 >= 2, # cuts applied on top of FO tau
                                                       selectJet = lambda jet: abs(jet.eta)<2.4,
                                                       selectFatJet = lambda fatjet: abs(fatjet.eta)<2.4,
                                                       coneptdef = lambda lep: lep.pt,
                                                       debug = True)
        def analyze(self,ev):
            self.sf1(ev)
    el = EventLoop([ Tester("tester") ])
    el.loop([tree], maxEvents = 50)
