# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/18a_callback.training.ipynb.

# %% ../../nbs/18a_callback.training.ipynb 2
from __future__ import annotations
from ..basics import *
from .progress import *
from .fp16 import *

# %% auto 0
__all__ = ['bn_types', 'ShortEpochCallback', 'GradientAccumulation', 'GradientClip', 'set_bn_eval', 'BnFreeze']

# %% ../../nbs/18a_callback.training.ipynb 6
class ShortEpochCallback(Callback):
    "Fit just `pct` of an epoch, then stop"
    def __init__(self,pct=0.01,short_valid=True): self.pct,self.short_valid = pct,short_valid
    def after_batch(self):
        if self.iter/self.n_iter < self.pct: return
        if self.training:    raise CancelTrainException
        if self.short_valid: raise CancelValidException

# %% ../../nbs/18a_callback.training.ipynb 10
class GradientAccumulation(Callback):
    "Accumulate gradients before updating weights"
    order,run_valid = MixedPrecision.order-4,False
    def __init__(self, n_acc=32): store_attr()
    def before_fit(self): self.count=0
    def after_loss(self): self.learn.loss_grad /= self.n_acc/find_bs(self.learn.yb)
    def before_step(self):
        "Skip weight update if we have not seen enough items"
        self.learn.loss_grad *= self.n_acc/find_bs(self.learn.yb) # log correct loss
        self.count += find_bs(self.learn.yb)
        if self.count<self.n_acc: raise CancelBatchException() # skip step/zero_grad
        else: self.count=0

# %% ../../nbs/18a_callback.training.ipynb 16
class GradientClip(Callback):
    "Clip norm of gradients"
    order=MixedPrecision.order+1
    def __init__(self,max_norm:float=1., norm_type:float=2.0): store_attr()
    def before_step(self): nn.utils.clip_grad_norm_(self.parameters(), self.max_norm, self.norm_type)

# %% ../../nbs/18a_callback.training.ipynb 23
bn_types = (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)

def set_bn_eval(m:nn.Module, use_eval=True)->None:
    "Set bn layers in eval mode for all recursive children of `m`."
    for l in m.children():
        if isinstance(l, bn_types) and not next(l.parameters()).requires_grad:
            if use_eval: l.eval()
            else:        l.train()
        set_bn_eval(l)

class BnFreeze(Callback):
    run_after=TrainEvalCallback
    "Freeze moving average statistics in all non-trainable batchnorm layers."
    def before_train(self):
        set_bn_eval(self.model)
