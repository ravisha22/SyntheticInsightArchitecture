"""Pandas Copy-on-Write Case Study — How scattered user complaints converged into CoW.

Real pandas history (2020-2023):
1. Users filed hundreds of issues about SettingWithCopyWarning, chained assignment,
   unpredictable copy/view semantics, and nullable dtype inconsistencies.
2. These looked like unrelated bug reports across indexing, dtypes, memory, and Arrow.
3. The pandas team eventually recognized the COMMON ROOT: mutable shared memory between
   DataFrames and views, and the solution was Copy-on-Write (PDEP-7, pandas 2.0+).

This scenario feeds ~30 representative issues as SIA events. The hypothesis:
SIA's tag-clustering and pressure-accumulation pipeline should detect the shared
"copy/view/semantics" pattern and commit to a goal resembling CoW BEFORE being told
about it — mirroring the multi-year insight the pandas maintainers reached.

Sources: pandas GitHub issues, PDEP-7, pandas 2.0 migration guide.
"""


def build_pandas_cow_scenario():
    """Build the pandas CoW case study as a sequence of temporal events.

    Events span cycles 1-35 (~months from 2020-2023). Categories look unrelated
    on the surface but share overlapping tags so SIA's clustering finds the pattern.
    """
    events = []

    # =========================================================================
    # PHASE 1: Early copy/view confusion (Cycles 1-6)
    # =========================================================================
    events.append({"cycle": 1, "type": "tension", "data": {
        "title": "SettingWithCopyWarning is confusing and inconsistent",
        "description": (
            "Users constantly encounter SettingWithCopyWarning but cannot predict "
            "when it fires. The warning text is unhelpful and the copy view semantics "
            "vary by operation, making it the most-asked-about pandas issue on StackOverflow."
        ),
        "stake_weight": 2.0,
    }})

    events.append({"cycle": 2, "type": "tension", "data": {
        "title": "Chained assignment behavior is unpredictable",
        "description": (
            "df['a'][mask] = val sometimes modifies the original DataFrame and "
            "sometimes silently operates on a copy. Whether chained indexing returns "
            "a view or copy depends on internal memory layout, not user intent."
        ),
        "stake_weight": 1.8,
    }})

    events.append({"cycle": 3, "type": "tension", "data": {
        "title": "df.loc assignment sometimes modifies original, sometimes does not",
        "description": (
            "Even the recommended df.loc[row, col] = val path has edge cases where "
            "the semantics differ. Slicing returns a view but boolean masking returns "
            "a copy, and users cannot tell which will happen."
        ),
        "stake_weight": 1.5,
    }})

    events.append({"cycle": 4, "type": "tension", "data": {
        "title": "Copy semantics differ between slice and boolean mask operations",
        "description": (
            "df[0:5] returns a view but df[df.x > 0] returns a copy. Both look like "
            "subsetting but have opposite copy view semantics. This inconsistency "
            "causes silent data corruption bugs in production pipelines."
        ),
        "stake_weight": 1.6,
    }})

    events.append({"cycle": 5, "type": "tension", "data": {
        "title": "No way to know if a DataFrame is a view or a copy",
        "description": (
            "There is no public API to inspect whether a DataFrame shares memory "
            "with another. Users must guess copy view status, leading to defensive "
            ".copy() calls everywhere and wasted memory."
        ),
        "stake_weight": 1.4,
    }})

    # =========================================================================
    # PHASE 2: Nullable dtype inconsistencies (Cycles 5-12)
    # =========================================================================
    events.append({"cycle": 6, "type": "tension", "data": {
        "title": "pd.NA behavior inconsistent with np.nan for nullable dtypes",
        "description": (
            "pd.NA propagates differently than np.nan in boolean and arithmetic "
            "contexts. Code that works with float NaN breaks with nullable Int64 "
            "dtype columns because NA semantics diverge."
        ),
        "stake_weight": 1.3,
    }})

    events.append({"cycle": 7, "type": "tension", "data": {
        "title": "Nullable Int64 dtype does not work with many operations",
        "description": (
            "The new nullable integer dtype Int64 is incompatible with groupby, merge, "
            "and many numpy operations. Users hit dtype coercion errors that force "
            "fallback to float64 with np.nan, defeating the purpose of nullable types."
        ),
        "stake_weight": 1.4,
    }})

    events.append({"cycle": 8, "type": "tension", "data": {
        "title": "Mixed nullable and non-nullable columns cause unexpected coercion",
        "description": (
            "Combining a nullable Int64 column with a regular int64 column via concat "
            "or merge silently coerces to object dtype. The dtype coercion rules are "
            "undocumented and inconsistent across operations."
        ),
        "stake_weight": 1.2,
    }})

    events.append({"cycle": 9, "type": "tension", "data": {
        "title": "ExtensionArray does not follow same rules as ndarray backing",
        "description": (
            "ExtensionArrays (backing nullable dtypes) have different copy view "
            "semantics, broadcasting rules, and dtype coercion behavior than numpy "
            "ndarrays. This creates two parallel code paths with different bugs."
        ),
        "stake_weight": 1.5,
    }})

    events.append({"cycle": 10, "type": "tension", "data": {
        "title": "BooleanDtype behaves differently than bool dtype",
        "description": (
            "pd.BooleanDtype with pd.NA does not work as a mask in .loc indexing "
            "or numpy operations. Users expect bool-like semantics but get dtype "
            "errors because the nullable extension dtype is not interchangeable."
        ),
        "stake_weight": 1.1,
    }})

    # =========================================================================
    # PHASE 3: Memory and performance complaints (Cycles 10-18)
    # =========================================================================
    events.append({"cycle": 11, "type": "tension", "data": {
        "title": "Unnecessary copies in groupby operations waste memory",
        "description": (
            "GroupBy internally copies the entire DataFrame even for simple "
            "aggregations. On large datasets this causes 2x memory usage and OOM "
            "errors. The copy is defensive because of mutable view semantics."
        ),
        "stake_weight": 1.7,
    }})

    events.append({"cycle": 12, "type": "tension", "data": {
        "title": "concat creates copies even when not needed",
        "description": (
            "pd.concat always copies input DataFrames even when the result could "
            "safely share memory. This doubles memory usage for a common operation "
            "because pandas cannot track view ownership."
        ),
        "stake_weight": 1.5,
    }})

    events.append({"cycle": 13, "type": "tension", "data": {
        "title": "Large DataFrame operations use 2x expected memory",
        "description": (
            "Method chains like df.rename().assign().drop() allocate a full copy "
            "at each step. Users with large datasets run out of memory because "
            "pandas makes defensive copies at every inplace operation boundary."
        ),
        "stake_weight": 1.8,
    }})

    events.append({"cycle": 14, "type": "tension", "data": {
        "title": "inplace parameter does not actually avoid copies",
        "description": (
            "Despite the name, inplace=True in drop, rename, and fillna still "
            "creates an internal copy before modifying. The parameter is misleading "
            "and does not reduce memory usage as users expect."
        ),
        "stake_weight": 1.6,
    }})

    events.append({"cycle": 15, "type": "tension", "data": {
        "title": "Method chaining forces defensive copies at every step",
        "description": (
            "Idiomatic pandas method chaining (df.pipe().assign().query()) cannot "
            "avoid copies because each method must assume its input may be a view "
            "that other code depends on. Copy-on-write semantics would fix this."
        ),
        "stake_weight": 1.7,
    }})

    # =========================================================================
    # PHASE 4: Arrow backend friction (Cycles 16-22)
    # =========================================================================
    events.append({"cycle": 16, "type": "tension", "data": {
        "title": "Arrow-backed string columns behave differently in indexing",
        "description": (
            "ArrowDtype string columns return Arrow arrays from indexing rather "
            "than numpy arrays. Copy view semantics, dtype coercion, and NA "
            "handling all differ from the numpy-backed string path."
        ),
        "stake_weight": 1.3,
    }})

    events.append({"cycle": 17, "type": "tension", "data": {
        "title": "Conversion between Arrow and numpy dtypes loses information",
        "description": (
            "Converting between Arrow-backed and numpy-backed columns silently "
            "drops nullable dtype information and changes NA to np.nan. The dtype "
            "coercion is lossy and not round-trippable."
        ),
        "stake_weight": 1.2,
    }})

    events.append({"cycle": 18, "type": "tension", "data": {
        "title": "Arrow arrays do not support all pandas operations consistently",
        "description": (
            "Many pandas operations assume numpy ndarray internals. Arrow-backed "
            "columns fail or produce wrong results in groupby, pivot, and merge "
            "because the copy view and memory model differs."
        ),
        "stake_weight": 1.4,
    }})

    # =========================================================================
    # PHASE 5: Cross-cutting indexing confusion (Cycles 19-25)
    # =========================================================================
    events.append({"cycle": 19, "type": "tension", "data": {
        "title": "Inconsistent behavior between loc, iloc, and __getitem__",
        "description": (
            "df.loc, df.iloc, and df[] have different copy view semantics for the "
            "same logical selection. loc returns views for slices but copies for "
            "lists. __getitem__ rules depend on the dtype of the indexer."
        ),
        "stake_weight": 1.6,
    }})

    events.append({"cycle": 20, "type": "tension", "data": {
        "title": "DataFrame constructor copy behavior varies by input type",
        "description": (
            "pd.DataFrame(data, copy=False) shares memory with ndarray input but "
            "copies dict input. The copy semantics of the constructor depend on "
            "the input type in undocumented ways."
        ),
        "stake_weight": 1.3,
    }})

    events.append({"cycle": 21, "type": "tension", "data": {
        "title": "Setting values on filtered DataFrames is fragile and unpredictable",
        "description": (
            "df[df.x > 0]['y'] = 1 silently fails because the boolean mask returns "
            "a copy. Users expect mutation but get nothing. The copy view semantics "
            "make write-after-filter a persistent footgun."
        ),
        "stake_weight": 1.8,
    }})

    # =========================================================================
    # PHASE 6: Seeds — partial solution ideas emerge (Cycles 8-28)
    # =========================================================================

    # Early seed: someone notices the copy/view root cause
    events.append({"cycle": 8, "type": "seed", "data": {
        "description": (
            "What if all pandas operations returned copies by default, with "
            "copy-on-write optimization to avoid actual memory duplication until "
            "mutation occurs?"
        ),
        "tags": [
            "copy", "view", "semantics", "copy-on-write", "memory",
            "indexing", "chained-assignment", "inplace",
        ],
    }})

    # Nullable dtype unification seed
    events.append({"cycle": 12, "type": "seed", "data": {
        "description": (
            "What if pandas had a unified nullable dtype system where every column "
            "natively supports NA without falling back to float64 or object?"
        ),
        "tags": [
            "nullable", "dtype", "NA", "coercion", "extension-array",
            "arrow", "semantics", "memory",
        ],
    }})

    # Arrow backend seed
    events.append({"cycle": 18, "type": "seed", "data": {
        "description": (
            "What if Arrow was the default memory backend for pandas, giving "
            "consistent dtype semantics, zero-copy interop, and built-in nullable "
            "types?"
        ),
        "tags": [
            "arrow", "dtype", "nullable", "memory", "copy",
            "extension-array", "semantics", "coercion",
        ],
    }})

    # CoW crystallization seed — the unifying idea
    events.append({"cycle": 22, "type": "seed", "data": {
        "description": (
            "Copy-on-Write semantics would unify indexing behavior: every operation "
            "returns a new object, mutations never propagate to parents, and actual "
            "memory copies are deferred until write. This resolves copy view "
            "confusion, eliminates SettingWithCopyWarning, and enables zero-copy "
            "method chaining."
        ),
        "tags": [
            "copy-on-write", "copy", "view", "semantics", "indexing",
            "chained-assignment", "inplace", "memory", "dtype",
            "SettingWithCopyWarning", "method-chaining",
        ],
    }})

    # Deprecation seed — inplace must go
    events.append({"cycle": 25, "type": "seed", "data": {
        "description": (
            "If Copy-on-Write is adopted, the inplace parameter becomes meaningless "
            "and should be deprecated. All mutation should be explicit assignment."
        ),
        "tags": [
            "copy-on-write", "inplace", "semantics", "memory",
            "chained-assignment", "copy", "view",
        ],
    }})

    # =========================================================================
    # PHASE 7: Resource pressure — maintenance burden mounts (Cycles 15-30)
    # =========================================================================
    events.append({"cycle": 15, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 5,
    }})
    events.append({"cycle": 20, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 8,
    }})
    events.append({"cycle": 25, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 10,
    }})
    events.append({"cycle": 28, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 12,
    }})

    # =========================================================================
    # PHASE 8: Late-stage reinforcement tensions (Cycles 26-32)
    # =========================================================================
    events.append({"cycle": 26, "type": "tension", "data": {
        "title": "SettingWithCopyWarning cannot be fixed without changing copy view model",
        "description": (
            "Core maintainers acknowledge that SettingWithCopyWarning is unfixable "
            "under current semantics. The view mutation model is the root cause and "
            "only copy-on-write or always-copy would resolve it."
        ),
        "stake_weight": 2.0,
    }})

    events.append({"cycle": 27, "type": "tension", "data": {
        "title": "Deprecating inplace parameter blocked by copy view ambiguity",
        "description": (
            "Cannot deprecate inplace without a clear copy view contract. Users rely "
            "on inplace for memory efficiency but it does not actually help. "
            "Copy-on-write would make inplace redundant."
        ),
        "stake_weight": 1.5,
    }})

    events.append({"cycle": 28, "type": "tension", "data": {
        "title": "New Arrow dtypes cannot integrate cleanly with numpy view model",
        "description": (
            "Arrow-backed columns need copy-on-write semantics to coexist with numpy "
            "columns. The view model prevents unified dtype handling across backends "
            "and blocks the Arrow migration."
        ),
        "stake_weight": 1.6,
    }})

    # Late seed: explicit PDEP proposal framing
    events.append({"cycle": 30, "type": "seed", "data": {
        "description": (
            "PDEP-7 proposal: adopt Copy-on-Write as the default for pandas 2.0. "
            "Every indexing operation returns a new object. Writes trigger a lazy "
            "copy. SettingWithCopyWarning is removed. inplace is deprecated."
        ),
        "tags": [
            "copy-on-write", "PDEP-7", "copy", "view", "semantics",
            "SettingWithCopyWarning", "inplace", "indexing", "memory",
            "method-chaining", "arrow", "dtype", "chained-assignment",
        ],
    }})

    # Final resource pressure — pandas 2.0 release timeline
    events.append({"cycle": 32, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 10,
    }})

    return events
