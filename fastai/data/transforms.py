# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/05_data.transforms.ipynb (unless otherwise specified).


from __future__ import annotations


__all__ = ['get_files', 'FileGetter', 'image_extensions', 'get_image_files', 'ImageGetter', 'get_text_files',
           'ItemGetter', 'AttrGetter', 'RandomSplitter', 'TrainTestSplitter', 'IndexSplitter', 'EndSplitter',
           'GrandparentSplitter', 'FuncSplitter', 'MaskSplitter', 'FileSplitter', 'ColSplitter', 'RandomSubsetSplitter',
           'parent_label', 'RegexLabeller', 'ColReader', 'CategoryMap', 'Categorize', 'Category', 'MultiCategorize',
           'MultiCategory', 'OneHotEncode', 'EncodedMultiCategorize', 'RegressionSetup', 'get_c', 'ToTensor',
           'IntToFloatTensor', 'broadcast_vec', 'Normalize']

# Cell
#nbdev_comment from __future__ import annotations
from ..torch_basics import *
from .core import *
from .load import *
from .external import *

from sklearn.model_selection import train_test_split

import posixpath

# Cell
def _get_files(p, fs, extensions=None):
    p = Path(p)
    res = [p/f for f in fs if not f.startswith('.')
           and ((not extensions) or f'.{f.split(".")[-1].lower()}' in extensions)]
    return res

# Cell
def get_files(path, extensions=None, recurse=True, folders=None, followlinks=True):
    "Get all the files in `path` with optional `extensions`, optionally with `recurse`, only in `folders`, if specified."
    path = Path(path)
    folders=L(folders)
    extensions = setify(extensions)
    extensions = {e.lower() for e in extensions}
    if recurse:
        res = []
        for i,(p,d,f) in enumerate(os.walk(path, followlinks=followlinks)): # returns (dirpath, dirnames, filenames)
            if len(folders) !=0 and i==0: d[:] = [o for o in d if o in folders]
            else:                         d[:] = [o for o in d if not o.startswith('.')]
            if len(folders) !=0 and i==0 and '.' not in folders: continue
            res += _get_files(p, f, extensions)
    else:
        f = [o.name for o in os.scandir(path) if o.is_file()]
        res = _get_files(path, f, extensions)
    return L(res)

# Cell
def FileGetter(suf='', extensions=None, recurse=True, folders=None):
    "Create `get_files` partial function that searches path suffix `suf`, only in `folders`, if specified, and passes along args"
    def _inner(o, extensions=extensions, recurse=recurse, folders=folders):
        return get_files(o/suf, extensions, recurse, folders)
    return _inner

# Cell
image_extensions = set(k for k,v in mimetypes.types_map.items() if v.startswith('image/'))

# Cell
def get_image_files(path, recurse=True, folders=None):
    "Get image files in `path` recursively, only in `folders`, if specified."
    return get_files(path, extensions=image_extensions, recurse=recurse, folders=folders)

# Cell
def ImageGetter(suf='', recurse=True, folders=None):
    "Create `get_image_files` partial that searches suffix `suf` and passes along `kwargs`, only in `folders`, if specified"
    def _inner(o, recurse=recurse, folders=folders): return get_image_files(o/suf, recurse, folders)
    return _inner

# Cell
def get_text_files(path, recurse=True, folders=None):
    "Get text files in `path` recursively, only in `folders`, if specified."
    return get_files(path, extensions=['.txt'], recurse=recurse, folders=folders)

# Cell
class ItemGetter(ItemTransform):
    "Creates a proper transform that applies `itemgetter(i)` (even on a tuple)"
    _retain = False
    def __init__(self, i): self.i = i
    def encodes(self, x): return x[self.i]

# Cell
class AttrGetter(ItemTransform):
    "Creates a proper transform that applies `attrgetter(nm)` (even on a tuple)"
    _retain = False
    def __init__(self, nm, default=None): store_attr()
    def encodes(self, x): return getattr(x, self.nm, self.default)

# Cell
def RandomSplitter(valid_pct=0.2, seed=None):
    "Create function that splits `items` between train/val with `valid_pct` randomly."
    def _inner(o):
        if seed is not None: torch.manual_seed(seed)
        rand_idx = L(list(torch.randperm(len(o)).numpy()))
        cut = int(valid_pct * len(o))
        return rand_idx[cut:],rand_idx[:cut]
    return _inner

# Cell
def TrainTestSplitter(test_size=0.2, random_state=None, stratify=None, train_size=None, shuffle=True):
    "Split `items` into random train and test subsets using sklearn train_test_split utility."
    def _inner(o, **kwargs):
        train,valid = train_test_split(range_of(o), test_size=test_size, random_state=random_state,
                                        stratify=stratify, train_size=train_size, shuffle=shuffle)
        return L(train), L(valid)
    return _inner

# Cell
def IndexSplitter(valid_idx):
    "Split `items` so that `val_idx` are in the validation set and the others in the training set"
    def _inner(o):
        train_idx = np.setdiff1d(np.array(range_of(o)), np.array(valid_idx))
        return L(train_idx, use_list=True), L(valid_idx, use_list=True)
    return _inner

# Cell
def EndSplitter(valid_pct=0.2, valid_last=True):
    "Create function that splits `items` between train/val with `valid_pct` at the end if `valid_last` else at the start. Useful for ordered data."
    assert 0<valid_pct<1, "valid_pct must be in (0,1)"
    def _inner(o):
        idxs = range_of(o)
        cut = int(valid_pct * len(o))
        return (idxs[:-cut], idxs[-cut:]) if valid_last else (idxs[cut:],idxs[:cut])
    return _inner

# Cell
def _grandparent_idxs(items, name):
    def _inner(items, name): return mask2idxs(Path(o).parent.parent.name == name for o in items)
    return [i for n in L(name) for i in _inner(items,n)]

# Cell
def GrandparentSplitter(train_name='train', valid_name='valid'):
    "Split `items` from the grand parent folder names (`train_name` and `valid_name`)."
    def _inner(o):
        return _grandparent_idxs(o, train_name),_grandparent_idxs(o, valid_name)
    return _inner

# Cell
def FuncSplitter(func):
    "Split `items` by result of `func` (`True` for validation, `False` for training set)."
    def _inner(o):
        val_idx = mask2idxs(func(o_) for o_ in o)
        return IndexSplitter(val_idx)(o)
    return _inner

# Cell
def MaskSplitter(mask):
    "Split `items` depending on the value of `mask`."
    def _inner(o): return IndexSplitter(mask2idxs(mask))(o)
    return _inner

# Cell
def FileSplitter(fname):
    "Split `items` by providing file `fname` (contains names of valid items separated by newline)."
    valid = Path(fname).read_text().split('\n')
    def _func(x): return x.name in valid
    def _inner(o): return FuncSplitter(_func)(o)
    return _inner

# Cell
def ColSplitter(col='is_valid'):
    "Split `items` (supposed to be a dataframe) by value in `col`"
    def _inner(o):
        assert isinstance(o, pd.DataFrame), "ColSplitter only works when your items are a pandas DataFrame"
        valid_idx = (o.iloc[:,col] if isinstance(col, int) else o[col]).values.astype('bool')
        return IndexSplitter(mask2idxs(valid_idx))(o)
    return _inner

# Cell
def RandomSubsetSplitter(train_sz, valid_sz, seed=None):
    "Take randoms subsets of `splits` with `train_sz` and `valid_sz`"
    assert 0 < train_sz < 1
    assert 0 < valid_sz < 1
    assert train_sz + valid_sz <= 1.

    def _inner(o):
        if seed is not None: torch.manual_seed(seed)
        train_len,valid_len = int(len(o)*train_sz),int(len(o)*valid_sz)
        idxs = L(list(torch.randperm(len(o)).numpy()))
        return idxs[:train_len],idxs[train_len:train_len+valid_len]
    return _inner

# Cell
def parent_label(o):
    "Label `item` with the parent folder name."
    return Path(o).parent.name

# Cell
class RegexLabeller():
    "Label `item` with regex `pat`."
    def __init__(self, pat, match=False):
        self.pat = re.compile(pat)
        self.matcher = self.pat.match if match else self.pat.search

    def __call__(self, o):
        o = str(o).replace(os.sep, posixpath.sep)
        res = self.matcher(o)
        assert res,f'Failed to find "{self.pat}" in "{o}"'
        return res.group(1)

# Cell
class ColReader(DisplayedTransform):
    "Read `cols` in `row` with potential `pref` and `suff`"
    def __init__(self, cols, pref='', suff='', label_delim=None):
        store_attr()
        self.pref = str(pref) + os.path.sep if isinstance(pref, Path) else pref
        self.cols = L(cols)

    def _do_one(self, r, c):
        o = r[c] if isinstance(c, int) or not c in getattr(r, '_fields', []) else getattr(r, c)
        if len(self.pref)==0 and len(self.suff)==0 and self.label_delim is None: return o
        if self.label_delim is None: return f'{self.pref}{o}{self.suff}'
        else: return o.split(self.label_delim) if len(o)>0 else []

    def __call__(self, o, **kwargs):
        if len(self.cols) == 1: return self._do_one(o, self.cols[0])
        return L(self._do_one(o, c) for c in self.cols)

# Cell
class CategoryMap(CollBase):
    "Collection of categories with the reverse mapping in `o2i`"
    def __init__(self, col, sort=True, add_na=False, strict=False):
        if is_categorical_dtype(col):
            items = L(col.cat.categories, use_list=True)
            #Remove non-used categories while keeping order
            if strict: items = L(o for o in items if o in col.unique())
        else:
            if not hasattr(col,'unique'): col = L(col, use_list=True)
            # `o==o` is the generalized definition of non-NaN used by Pandas
            items = L(o for o in col.unique() if o==o)
            if sort: items = items.sorted()
        self.items = '#na#' + items if add_na else items
        self.o2i = defaultdict(int, self.items.val2idx()) if add_na else dict(self.items.val2idx())

    def map_objs(self,objs):
        "Map `objs` to IDs"
        return L(self.o2i[o] for o in objs)

    def map_ids(self,ids):
        "Map `ids` to objects in vocab"
        return L(self.items[o] for o in ids)

    def __eq__(self,b): return all_equal(b,self)

# Cell
class Categorize(DisplayedTransform):
    "Reversible transform of category string to `vocab` id"
    loss_func,order=CrossEntropyLossFlat(),1
    def __init__(self, vocab=None, sort=True, add_na=False):
        if vocab is not None: vocab = CategoryMap(vocab, sort=sort, add_na=add_na)
        store_attr()

    def setups(self, dsets):
        if self.vocab is None and dsets is not None: self.vocab = CategoryMap(dsets, sort=self.sort, add_na=self.add_na)
        self.c = len(self.vocab)

    def encodes(self, o):
        try:
            return TensorCategory(self.vocab.o2i[o])
        except KeyError as e:
            raise KeyError(f"Label '{o}' was not included in the training dataset") from e
    def decodes(self, o): return Category      (self.vocab    [o])

# Cell
class Category(str, ShowTitle): _show_args = {'label': 'category'}

# Cell
class MultiCategorize(Categorize):
    "Reversible transform of multi-category strings to `vocab` id"
    loss_func,order=BCEWithLogitsLossFlat(),1
    def __init__(self, vocab=None, add_na=False): super().__init__(vocab=vocab,add_na=add_na,sort=vocab==None)

    def setups(self, dsets):
        if not dsets: return
        if self.vocab is None:
            vals = set()
            for b in dsets: vals = vals.union(set(b))
            self.vocab = CategoryMap(list(vals), add_na=self.add_na)

    def encodes(self, o):
        if not all(elem in self.vocab.o2i.keys() for elem in o):
            diff = [elem for elem in o if elem not in self.vocab.o2i.keys()]
            diff_str = "', '".join(diff)
            raise KeyError(f"Labels '{diff_str}' were not included in the training dataset")
        return TensorMultiCategory([self.vocab.o2i[o_] for o_ in o])
    def decodes(self, o): return MultiCategory      ([self.vocab    [o_] for o_ in o])

# Cell
class MultiCategory(L):
    def show(self, ctx=None, sep=';', color='black', **kwargs):
        return show_title(sep.join(self.map(str)), ctx=ctx, color=color, **kwargs)

# Cell
class OneHotEncode(DisplayedTransform):
    "One-hot encodes targets"
    order=2
    def __init__(self, c=None): store_attr()

    def setups(self, dsets):
        if self.c is None: self.c = len(L(getattr(dsets, 'vocab', None)))
        if not self.c: warn("Couldn't infer the number of classes, please pass a value for `c` at init")

    def encodes(self, o): return TensorMultiCategory(one_hot(o, self.c).float())
    def decodes(self, o): return one_hot_decode(o, None)

# Cell
class EncodedMultiCategorize(Categorize):
    "Transform of one-hot encoded multi-category that decodes with `vocab`"
    loss_func,order=BCEWithLogitsLossFlat(),1
    def __init__(self, vocab):
        super().__init__(vocab, sort=vocab==None)
        self.c = len(vocab)
    def encodes(self, o): return TensorMultiCategory(tensor(o).float())
    def decodes(self, o): return MultiCategory (one_hot_decode(o, self.vocab))

# Cell
class RegressionSetup(DisplayedTransform):
    "Transform that floatifies targets"
    loss_func=MSELossFlat()
    def __init__(self, c=None): store_attr()

    def encodes(self, o): return tensor(o).float()
    def decodes(self, o): return TitledFloat(o) if o.ndim==0 else TitledTuple(o_.item() for o_ in o)
    def setups(self, dsets):
        if self.c is not None: return
        try: self.c = len(dsets[0]) if hasattr(dsets[0], '__len__') else 1
        except: self.c = 0

# Cell
def get_c(dls):
    if getattr(dls, 'c', False): return dls.c
    if getattr(getattr(dls.train, 'after_item', None), 'c', False): return dls.train.after_item.c
    if getattr(getattr(dls.train, 'after_batch', None), 'c', False): return dls.train.after_batch.c
    vocab = getattr(dls, 'vocab', [])
    if len(vocab) > 0 and is_listy(vocab[-1]): vocab = vocab[-1]
    return len(vocab)

# Cell
class ToTensor(Transform):
    "Convert item to appropriate tensor class"
    order = 5

# Cell
class IntToFloatTensor(DisplayedTransform):
    "Transform image to float tensor, optionally dividing by 255 (e.g. for images)."
    order = 10 #Need to run after PIL transforms on the GPU
    def __init__(self, div=255., div_mask=1): store_attr()
    def encodes(self, o:TensorImage): return o.float().div_(self.div)
    def encodes(self, o:TensorMask ): return o.long() // self.div_mask
    def decodes(self, o:TensorImage): return ((o.clamp(0., 1.) * self.div).long()) if self.div else o

# Cell
def broadcast_vec(dim, ndim, *t, cuda=True):
    "Make a vector broadcastable over `dim` (out of `ndim` total) by prepending and appending unit axes"
    v = [1]*ndim
    v[dim] = -1
    f = to_device if cuda else noop
    return [f(tensor(o).view(*v)) for o in t]

# Cell
@docs
class Normalize(DisplayedTransform):
    "Normalize/denorm batch of `TensorImage`"
    parameters,order = L('mean', 'std'),99
    def __init__(self, mean=None, std=None, axes=(0,2,3)): store_attr()

    @classmethod
    def from_stats(cls, mean, std, dim=1, ndim=4, cuda=True): return cls(*broadcast_vec(dim, ndim, mean, std, cuda=cuda))

    def setups(self, dl:DataLoader):
        if self.mean is None or self.std is None:
            x,*_ = dl.one_batch()
            self.mean,self.std = x.mean(self.axes, keepdim=True),x.std(self.axes, keepdim=True)+1e-7

    def encodes(self, x:TensorImage): return (x-self.mean) / self.std
    def decodes(self, x:TensorImage):
        f = to_cpu if x.device.type=='cpu' else noop
        return (x*f(self.std) + f(self.mean))

    _docs=dict(encodes="Normalize batch", decodes="Denormalize batch")