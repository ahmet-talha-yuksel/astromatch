"""Public API; lazy exports keep the legacy backend dependency-free."""
__all__=['load_dataset','list_targets','rank','explain','heat','DataPaths','Dataset','TargetSummary','RankResult','Explanation','HeatPoint']

def __getattr__(name):
    if name not in __all__: raise AttributeError(name)
    if name in ('DataPaths','Dataset','TargetSummary','RankResult','Explanation','HeatPoint'):
        from . import models
        return getattr(models,name)
    if name=='load_dataset':
        from .io import load_dataset
        return load_dataset
    from . import ranking
    return getattr(ranking,name)
